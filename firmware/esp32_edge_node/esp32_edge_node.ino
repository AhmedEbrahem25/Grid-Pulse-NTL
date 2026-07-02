/*
 * Grid-Pulse NTL — ESP32 Edge Node
 * Reads an SCT-013 current transformer via a burden + DC-bias circuit, computes
 * RMS current (EmonLib), estimates power, and POSTs a contract-valid payload to
 * the FastAPI backend. See README.md for the wiring (this is the part that
 * fries the ADC if you skip it: the CT output is AC and swings negative).
 *
 * Libraries (Arduino IDE / PlatformIO):
 *   - EmonLib   (Emon energy monitoring)
 * Board: any ESP32 dev module.
 */
#include <WiFi.h>
#include <HTTPClient.h>
#include <time.h>
#include "EmonLib.h"
#include "config.h"

EnergyMonitor emon1;
unsigned long seq = 0;

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
  // EmonLib: map the ADC pin + calibration factor (turns_ratio / burden_ohms).
  emon1.current(CT_ADC_PIN, CAL_FACTOR);
  connectWiFi();
}

String buildPayload(double irms, double active, double apparent, double pf) {
  unsigned long ts = (unsigned long) time(nullptr);
  String s = "{";
  s += "\"schema_version\":\"1.0\",";
  s += "\"device_id\":\"" DEVICE_ID "\",";
  s += "\"firmware\":\"1.0.0\",";
  s += "\"ts\":" + String(ts) + ",";
  s += "\"seq\":" + String(seq++) + ",";
  s += "\"site\":{\"transformer_id\":\"" TRANSFORMER_ID "\"},";
  s += "\"measurement\":{\"window_ms\":" + String(POST_PERIOD_MS) + ",";
  s += "\"energy_wh_interval\":" + String(active * (POST_PERIOD_MS/1000.0) / 3600.0, 4) + ",";
  s += "\"phases\":[{\"phase\":\"single\",";
  s += "\"i_rms_a\":" + String(irms, 2) + ",";
  s += "\"v_rms_v\":" + String((double)NOMINAL_V, 1) + ",";
  s += "\"p_active_w\":" + String(active, 1) + ",";
  s += "\"s_apparent_va\":" + String(apparent, 1) + ",";
  s += "\"power_factor\":" + String(pf, 3) + ",";
  s += "\"freq_hz\":" + String((double)LINE_FREQ, 2) + ",";
  s += "\"thd_i_pct\":0}]},";
  s += "\"env\":{\"temp_c\":" + String((double)TEMP_C, 1) + "}";
  s += "}";
  return s;
}

void loop() {
  if (WiFi.status() != WL_CONNECTED) connectWiFi();

  double irms     = emon1.calcIrms(ADC_SAMPLES);   // amps RMS
  double apparent = NOMINAL_V * irms;              // VA
  double pf       = ASSUMED_PF;                    // measure with a voltage sensor for real PF
  double active   = apparent * pf;                 // W

  String body = buildPayload(irms, active, apparent, pf);

  HTTPClient http;
  http.begin(INGEST_URL);
  http.addHeader("Content-Type", "application/json");
  http.addHeader("Authorization", "Bearer " INGEST_TOKEN);
  int code = http.POST(body);
  Serial.printf("Irms=%.2fA  P=%.0fW  -> %d\n", irms, active, code);
  http.end();

  delay(POST_PERIOD_MS);
}
