# Grid‑Pulse NTL — Tasks & Roles

*Part of the plan set · see also: [03-timeline-96h](03-timeline-96h.md) · [01-architecture](01-architecture.md) · [02-detection-and-ai](02-detection-and-ai.md)*

> A balanced team beats 4 backend devs. Because there's **hardware**, one person owns the ESP32 + circuit end‑to‑end. One person owns the pitch from Day 2.

---

## 1. Roles

| Role | Person | Owns | Docs |
|---|---|---|---|
| **HW/FW** | electronics‑comfortable member (or the user) | ESP32, signal‑conditioning circuit, calibration, firmware, payload | `firmware/`, [01](01-architecture.md) |
| **BE/AI** | *the user* (systems/AI lead) | FastAPI + contract, Redis/Celery, the whole detection + AI pipeline | [01](01-architecture.md), [02](02-detection-and-ai.md) |
| **FE** | frontend dev | dashboard: map, live charts, verdict badges, XAI panel, alerts | [01](01-architecture.md) API |
| **PM** | presenter/PM | rubric, demo script, slides, timing, glue, fallback video, B2G story | [05](05-demo-pitch.md) |

*3‑person team:* HW/FW + BE/AI can be one strong person for the POC; PM doubles as FE helper.

## 2. Bill of Materials (POC — buy in Phase 0)

| Item | Qty | ~Price (EGP) | Note |
|---|---|---|---|
| ESP32 devkit | 1 | ~250 | Wi‑Fi + ADC |
| **SCT‑013‑000** (100A/50mA) | 1 | ~350 | current‑output, **needs burden** |
| Burden resistor 33Ω (¼W) | 1 | ~5 | sets output voltage |
| Resistors 10kΩ ×2 | 2 | ~5 | 1.65V bias divider |
| Capacitor 10µF | 1 | ~5 | bias filtering |
| Breadboard + jumpers | 1 | ~100 | — |
| Lamp (registered load) + hair‑dryer/heater (theft load) | — | on hand | the demo |
| *(optional)* DHT22 temp sensor | 1 | ~150 | real `temp_c`, else simulate |

Total ≈ **1,000 EGP**. Production upgrade path (Rogowski coils, IP65) is a **pitch slide**, not a purchase.

## 3. Task backlog (with acceptance criteria + deps)

### Foundation
| # | Task | Owner | AC | Deps |
|---|---|---|---|---|
| F1 | Repo + `docker-compose.yml` + `.env.example` + CI | BE/AI | `docker-compose up` runs api+redis+worker | — |
| F2 | Freeze **Strict API Contract** (JSON Schema + Pydantic) | BE/AI | malformed payload → 422 | — |
| F3 | Seed transformers + registered meters | BE/AI | `GET /transformers` rich | F1 |

### Hardware / Firmware (HW/FW)
| # | Task | AC | Deps |
|---|---|---|---|
| H1 | Signal‑conditioning circuit (burden+bias+cap) | ADC never sees negative V; stable midpoint 1.65V | BOM |
| H2 | Read CT + RMS (EmonLib) + calibrate | current within ±5% of reference | H1 |
| H3 | Compute PF, freq, FFT/THD | plausible PF/THD on serial | H2 |
| H4 | Build + POST payload per contract over Wi‑Fi | `/ingest` returns 200 | H3, F2 |
| H5 | `temp_c` (DHT22 or injected) | field populated | H4 |

### Backend + AI (BE/AI)
| # | Task | AC | Deps |
|---|---|---|---|
| B1 | `/ingest` validate+persist+enqueue; `/meters/reading`; WS | reading stored + pushed | F1,F2 |
| B2 | **Energy‑balance** module | `measured_loss_w` correct on a known case | B1,F3 |
| B3 | **Tech‑loss regressor** (train + load + infer) | `tech_loss_expected_w`, `residual_w` | ML1 |
| B4 | **Harmonics/PF** + **IsolationForest anomaly** | scores produced | B1 |
| B5 | **Decision fusion + XAI** → Verdict | label/confidence/theft_w/explanation | B2,B3,B4 |
| B6 | `GET /verdicts`, `POST /verdicts/{id}/status` | list + status update | B5 |

### ML
| # | Task | AC | Deps |
|---|---|---|---|
| ML1 | `generate_dataset.py` (physics‑seeded) + `train.py` | `ml/artifacts/*.pkl` | F1 |

### Simulator (BE/AI or PM) — **critical fallback**
| # | Task | AC | Deps |
|---|---|---|---|
| S1 | `simulate.py` emits `normal` payloads | dashboard shows NORMAL | B1 |
| S2 | `POST /sim/scenario` = `normal\|technical\|theft` | each beat reproducible | S1,B5 |

### Frontend (FE)
| # | Task | AC | Deps |
|---|---|---|---|
| U1 | Map + transformer cards + live power chart | live via WS/poll | B1 |
| U2 | Verdict badge + loss/baseline numbers | NORMAL/TECHNICAL visible | B3 |
| U3 | **Red critical alert + XAI panel + theft watts** | theft beat pops | B5 |
| U4 | Alerts list + status buttons; polish/empty states | no dead ends | B6 |

### Pitch (PM)
| # | Task | AC | Deps |
|---|---|---|---|
| P1 | Rubric map + 30B EGP problem story + B2G model | 1 slide each | — |
| P2 | 90 s script + deck + **fallback video** | timed < 90 s | Day‑3 aha |

## 4. Critical path

`F2 → B1 → (H4 or S2) → B2 → ML1/B3 → B4 → B5 → U3` → **3‑beat aha done**. Parallelize HW bring‑up (H1‑H5) with the simulator so backend never waits on hardware.

## 5. Git / team rules

`main` protected & always `docker-compose`‑runnable · `feat/<area>` branches · small PRs, one review, squash · conventional commits · secrets in env only (rotate `INGEST_TOKEN` before public demo) · CI green (lint + backend unit test) to merge.

## 6. Definition of Done (per task)

Merged to `main` · stack still runs via compose · demo path manual‑checked · (BE) a unit test for the detection math. Works‑only‑locally‑on‑my‑laptop ≠ done.
