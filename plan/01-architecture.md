# Grid‑Pulse NTL — Architecture

*Part of the plan set · see also: [00-overview](00-overview.md) · [02-detection-and-ai](02-detection-and-ai.md) · [04-tasks-roles](04-tasks-roles.md)*

> Canonical contract. The Edge→Backend payload here **must** equal `contracts/edge_telemetry.schema.json`. Detection field names must match [02](02-detection-and-ai.md).

---

## 1. System diagram

```
  DISTRIBUTION TRANSFORMER (POC: a "street" load bank)
        │  (busbar / feeder)
   ┌─────┴───────────────┐
   │  CT sensor (SCT-013) │  clip-on, non-invasive
   └─────┬───────────────┘
         │ analog (conditioned: burden + 1.65V bias + cap)
   ┌─────┴───────────────┐   Wi-Fi (POC) / LoRaWAN (prod)   ┌───────────────────────────────┐
   │  ESP32 Edge Node     │ ───── JSON payload (contract) ─▶ │ FastAPI  /ingest              │
   │  EmonLib RMS + FFT   │                                  │  • validate Strict Contract   │
   │  → I_rms,P,PF,THD    │                                  │  • enqueue → Redis            │
   └──────────────────────┘                                  └───────────────┬───────────────┘
                                                                             │
   registered smart-meter reads ──────────────────────────────▶  Redis queue │
                                                                             ▼
                                                          ┌───────────────────────────────┐
                                                          │ Celery worker(s)              │
                                                          │  energy-balance → tech-loss AI │
                                                          │  → harmonics → anomaly →decide │
                                                          │  → verdict + XAI               │
                                                          └───────────────┬───────────────┘
                                                                          │ store + WS push
                                                       ┌──────────────────┴──────────────────┐
                                                       │ Dashboard (map · verdict · XAI · Wh)  │
                                                       └───────────────────────────────────────┘
```

The **Edge does light DSP** (RMS, power factor, FFT/THD) so we ship *features*, not raw waveforms — tiny payloads, scalable to thousands of transformers.

## 2. Stack & rationale

| Layer | Choice | Why (96 h) |
|---|---|---|
| Edge firmware | **ESP32 + Arduino/C++**, EmonLib, arduinoFFT | cheap, Wi‑Fi built‑in, does RMS/FFT locally |
| Sensor (POC) | **SCT‑013‑000** (100A/50mA, no burden) + **33Ω burden + 1.65V bias + 10µF** | current‑output CT; conditioning required before ADC ([firmware README]) |
| Ingest API | **FastAPI** + **Pydantic** (mirrors the JSON Schema) | validates the Strict Contract, rejects junk (zero‑trust) |
| Queue | **Redis** | absorb bursts from many transformers |
| Workers | **Celery** | async AI inference; "looks like real microservices" to judges |
| AI | **scikit‑learn / XGBoost** (tech‑loss regression + IsolationForest) | trains in seconds on synthetic data |
| Store | **SQLite** (hackathon) → Postgres later | zero setup for the demo |
| Realtime | **FastAPI WebSocket** (+ 2 s poll fallback) | live red‑alert on stage |
| Dashboard | **single‑page** (served by FastAPI) or Next.js if FE bandwidth | keep it demo‑simple |
| Deploy | **docker‑compose up** (api + redis + worker) | one command on stage |

## 3. Repo layout (at project root)

```
Hackathon Kafrelsha5/
├─ plan/                         # these docs
├─ contracts/
│  ├─ edge_telemetry.schema.json # THE Strict API Contract (JSON Schema)
│  └─ README.md                  # examples + rules
├─ firmware/esp32_edge_node/
│  ├─ esp32_edge_node.ino        # C++: sample → bias-removal → RMS → PF → FFT/THD → POST
│  ├─ config.h                   # wifi, endpoint, CALIBRATION, BURDEN, thresholds
│  └─ README.md                  # wiring (burden+bias+cap), calibration math
├─ backend/
│  ├─ app/
│  │  ├─ main.py                 # FastAPI: /ingest /meters /healthz + WS + dashboard
│  │  ├─ contract.py             # Pydantic models == JSON Schema
│  │  ├─ config.py store.py ws.py queue.py tasks.py
│  │  └─ detection/              # energy_balance · technical_loss · harmonics · anomaly · decision
│  ├─ requirements.txt  Dockerfile
├─ simulator/simulate.py         # emits normal/technical/theft payloads (no-HW demo + data)
├─ ml/ generate_dataset.py  train.py  artifacts/
├─ dashboard/index.html          # map + verdict + XAI (if not using Next.js)
├─ docker-compose.yml  .env.example  README.md
```

## 4. Data model (canonical)

```
Transformer { id, name, feeder_id, lat, lng, rated_kva, registered_meter_ids[] }
Meter       { id, transformer_id, customer_ref, registered: bool }
EdgeReading { id, transformer_id, ts, phase,
              i_rms_a, v_rms_v, p_active_w, s_apparent_va, power_factor, freq_hz,
              thd_i_pct, energy_wh_interval, temp_c, humidity_pct }   # from contract
MeterReading{ id, meter_id, ts, energy_wh_interval, p_active_w }      # registered consumption
Verdict     { id, transformer_id, ts, phase, label, confidence,
              measured_loss_w, tech_loss_expected_w, residual_w, theft_estimate_w,
              severity, explanation: json, status }
```

**Enums (single source of truth):**
- `Verdict.label` = `NORMAL | TECHNICAL_LOSS | NTL_THEFT_SUSPECTED`
- `Verdict.severity` = `info | low | medium | high | critical` (bands in [02](02-detection-and-ai.md#severity))
- `Verdict.status` = `open | dispatched | confirmed | dismissed`
- `EdgeReading.phase` = `L1 | L2 | L3 | single`

## 5. API surface (canonical)

| Method & path | Body | Returns |
|---|---|---|
| `POST /ingest` | Edge payload (**must match schema**) | `{accepted:true, reading_id}` or `422` |
| `POST /meters/reading` | `{meter_id, ts, energy_wh_interval, p_active_w}` | `{ok:true}` |
| `GET /transformers` | — | `[Transformer]` + latest verdict |
| `GET /transformers/{id}` | — | detail + recent readings + verdicts |
| `GET /verdicts?label&severity&status` | — | `[Verdict]` newest first |
| `POST /verdicts/{id}/status` | `{status}` | `Verdict` |
| `POST /sim/scenario` | `{transformer_id, scenario}` | `{ok:true}` (`normal\|technical\|theft`) |
| `GET /healthz` | — | `{status:"ok"}` |
| **WS** `/ws/stream` | — | events `edge_reading` · `verdict` · `transformer_status` |

## 6. Data flow (per interval)

```
ESP32 → POST /ingest → validate(contract) → persist EdgeReading → enqueue(Redis)
Celery worker:
   pull latest registered MeterReadings for this transformer (same window)
   energy_balance()          → measured_loss_w = P_edge − ΣP_meters
   technical_loss_model()    → tech_loss_expected_w  (from temp/load/time)
   residual_w = measured_loss_w − tech_loss_expected_w
   harmonics()               → PF/THD theft signal
   anomaly()                 → temporal outlier score
   decide()                  → label + confidence + theft_estimate_w + XAI
   persist Verdict → WS push "verdict" + "transformer_status"
```

## 7. Config & deploy

`.env.example`: `REDIS_URL`, `DATABASE_URL` (sqlite default), `INGEST_TOKEN` (edge auth), `TECH_LOSS_MODEL_PATH`, `RESIDUAL_ALERT_W` (default margin), `SIM_MODE`.
**Run:** `docker-compose up` → api :8000, redis, worker. Seed transformers + train tech‑loss model at boot. Then `python simulator/simulate.py` (or flash the ESP32).

## 8. Non‑goals (Phase 2 — pitch, don't build)

Smart‑contactor auto‑cutoff, TinyML on‑device inference, hardware crypto/anti‑tamper, Rogowski multi‑phase board, LoRaWAN gateway, full utility‑meter (AMI) integration. Name them as the scaling/defense roadmap.
