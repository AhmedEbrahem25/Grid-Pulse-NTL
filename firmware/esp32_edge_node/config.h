// Grid-Pulse NTL — Edge Node config. Copy/edit for your board & site.
#pragma once

// --- WiFi (hackathon: direct WiFi; production: swap for LoRaWAN/NB-IoT) ---
#define WIFI_SSID      "YOUR_WIFI"
#define WIFI_PASS      "YOUR_PASS"

// --- Backend ---
#define INGEST_URL     "http://192.168.1.100:8000/ingest"   // your FastAPI host
#define INGEST_TOKEN   "dev-token"                           // must match backend INGEST_TOKEN

// --- Identity / site ---
#define DEVICE_ID        "GP-EDGE-000123"   // must match ^GP-EDGE-[A-Z0-9]{4,12}$
#define TRANSFORMER_ID   "TX-KFS-0456"      // must match ^TX-[A-Z0-9-]{3,20}$

// --- Sensor / signal conditioning (SCT-013-000, 100A/50mA, NO internal burden) ---
// Burden resistor Rb=33ohm -> calibration factor = turns_ratio / Rb = 2000/33 ~= 60.6
// (If you use 22ohm -> ~90.9). Calibrate against a known load and adjust.
#define CT_ADC_PIN       34        // ESP32 ADC1 pin fed by the burden+bias divider (1.65V mid)
#define CAL_FACTOR       60.6      // EmonLib current calibration
#define ADC_SAMPLES      1480      // samples per calcIrms() call

// --- Electrical assumptions for the POC ---
// The SCT gives current only. Without a voltage sensor (e.g. ZMPT101B) we assume
// nominal voltage and a power factor; add voltage sensing to measure PF/THD for real.
#define NOMINAL_V        230.0
#define ASSUMED_PF       0.95      // replace with measured PF when voltage sensing is added
#define LINE_FREQ        50.0

// --- Ambient (DHT22 optional; else a fixed value the backend still uses) ---
#define TEMP_C           30.0      // wire a DHT22 to send real temp for the AI baseline

#define POST_PERIOD_MS   1000
