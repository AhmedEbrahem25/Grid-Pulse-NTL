/*
 * Grid-Pulse NTL — ESP32 Edge Node (voltage + current)
 *
 * Reads an SCT-013 current transformer AND a ZMPT101B voltage sensor via
 * burden + DC-bias circuits, computes REAL active power / power factor (EmonLib
 * calcVI), a windowed FFT for THD + the harmonic vector, and POSTs a
 * contract-valid payload to the FastAPI backend. See README.md for the wiring
 * (skip the bias and you fry the ADC: both sensor outputs are AC and swing negative).
 *
 * Libraries (Arduino IDE / PlatformIO):
 *   - EmonLib      (energy monitoring — voltage+current)
 *   - arduinoFFT   (>= 2.0)
 * Board: any ESP32 dev module.
 */
#include <WiFi.h>
#include <HTTPClient.h>
#include <time.h>
#include "EmonLib.h"
#include <arduinoFFT.h>
#include "config.h"

EnergyMonitor emon1;
unsigned long seq = 0;

// FFT working buffers
double vReal[FFT_N];
double vImag[FFT_N];
ArduinoFFT<double> FFT = ArduinoFFT<double>(vReal, vImag, FFT_N, FFT_FS);

void connectWiFi() {
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  Serial.print("WiFi");
  while (WiFi.status() != WL_CONNECTED) { delay(400); Serial.print("."); }
  Serial.printf(" connected: %s\n", WiFi.localIP().toString().c_str());
  // NTP so the contract's `ts` (epoch seconds) is valid (>= 1.7e9).
  configTime(0, 0, "pool.ntp.org", "time.nist.gov");
  time_t now = 0; int tries = 0;
  while (now < 1700000000 && tries++ < 20) { delay(500); now = time(nullptr); }
}

void setup() {
  Serial.begin(115200);
  // EmonLib: voltage channel (ZMPT101B) + current channel (SCT-013 via burden).
  emon1.voltage(V_ADC_PIN, V_CAL, PHASE_CAL);
  emon1.current(CT_ADC_PIN, CAL_FACTOR);
  connectWiFi();
}

// Sample the current channel and FFT it -> THD (%) + a harmonics[] JSON fragment
// (odd orders 3..15 as % of the fundamental). Fundamental sits on integer bin 5.
double measureHarmonics(String &harmonicsJson) {
  const uint32_t periodUs = (uint32_t)(1000000.0 / FFT_FS);
  for (uint16_t i = 0; i < FFT_N; i++) {
    uint32_t t0 = micros();
    vReal[i] = (double)(analogRead(CT_ADC_PIN) - ADC_BIAS);   // remove the 1.65V DC bias
    vImag[i] = 0.0;
    while (micros() - t0 < periodUs) { /* hold the sample rate */ }
  }
  FFT.windowing(FFTWindow::Hamming, FFTDirection::Forward);
  FFT.compute(FFTDirection::Forward);
  FFT.complexToMagnitude();

  const int bin1 = 5;                          // 50 Hz -> bin 5 (see FFT_FS)
  double fund = vReal[bin1];
  if (fund < 1.0) { harmonicsJson = "[]"; return 0.0; }

  double sumSq = 0.0;
  harmonicsJson = "[";
  bool first = true;
  for (int h = 3; h <= 15; h += 2) {           // odd harmonics 3,5,7,9,11,13,15
    int bin = bin1 * h;
    if (bin >= FFT_N / 2) break;
    double magPct = (vReal[bin] / fund) * 100.0;
    sumSq += (vReal[bin] * vReal[bin]);
    if (magPct >= 1.0) {                        // only ship meaningful bins (contract: <=16)
      if (!first) harmonicsJson += ",";
      harmonicsJson += "{\"h\":" + String(h) + ",\"mag_pct\":" + String(magPct, 1) + "}";
      first = false;
    }
  }
  harmonicsJson += "]";
  return (sqrt(sumSq) / fund) * 100.0;          // THD_I (%)
}

String buildPayload(double vrms, double irms, double active, double apparent,
                    double pf, double thd, const String &harmonicsJson) {
  unsigned long ts = (unsigned long) time(nullptr);
  String s = "{";
  s += "\"schema_version\":\"1.0\",";
  s += "\"device_id\":\"" DEVICE_ID "\",";
  s += "\"firmware\":\"1.1.0\",";
  s += "\"ts\":" + String(ts) + ",";
  s += "\"seq\":" + String(seq++) + ",";
  s += "\"site\":{\"transformer_id\":\"" TRANSFORMER_ID "\"},";
  s += "\"measurement\":{\"window_ms\":" + String(POST_PERIOD_MS) + ",";
  s += "\"energy_wh_interval\":" + String(active * (POST_PERIOD_MS/1000.0) / 3600.0, 4) + ",";
  s += "\"phases\":[{\"phase\":\"single\",";
  s += "\"i_rms_a\":" + String(irms, 2) + ",";
  s += "\"v_rms_v\":" + String(vrms, 1) + ",";
  s += "\"p_active_w\":" + String(active, 1) + ",";
  s += "\"s_apparent_va\":" + String(apparent, 1) + ",";
  s += "\"power_factor\":" + String(pf, 3) + ",";
  s += "\"freq_hz\":" + String((double)LINE_FREQ, 2) + ",";
  s += "\"thd_i_pct\":" + String(thd, 1) + ",";
  s += "\"harmonics\":" + harmonicsJson + "}]},";
  s += "\"env\":{\"temp_c\":" + String((double)TEMP_C, 1) + "}";
  s += "}";
  return s;
}

void loop() {
  if (WiFi.status() != WL_CONNECTED) connectWiFi();

  emon1.calcVI(VI_CROSSINGS, VI_TIMEOUT_MS);   // real V, I, P, PF
  double vrms     = emon1.Vrms;
  double irms     = emon1.Irms;
  double active   = emon1.realPower;
  double apparent = emon1.apparentPower;
  double pf       = emon1.powerFactor;
  if (pf < 0) pf = -pf;                          // contract: power_factor in [0,1]
  if (pf > 1) pf = 1.0;

  String harmonicsJson;
  double thd = measureHarmonics(harmonicsJson);

  String body = buildPayload(vrms, irms, active, apparent, pf, thd, harmonicsJson);

  HTTPClient http;
  http.begin(INGEST_URL);
  http.addHeader("Content-Type", "application/json");
  http.addHeader("Authorization", "Bearer " INGEST_TOKEN);
  int code = http.POST(body);
  Serial.printf("V=%.0f  I=%.2fA  P=%.0fW  PF=%.2f  THD=%.1f%%  -> %d\n",
                vrms, irms, active, pf, thd, code);
  http.end();

  delay(POST_PERIOD_MS);
}
