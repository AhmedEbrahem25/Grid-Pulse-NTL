# Grid‑Pulse NTL — Timeline

*Part of the plan set · see also: [04-tasks-roles](04-tasks-roles.md) · [02-detection-and-ai](02-detection-and-ai.md)*

> Event ~**11 July 2026**. Two phases: a **pre‑event runway (now → event)** to de‑risk hardware + train the AI, then the **~96 h on‑site build**. **Golden rules:** deploy Day 0 · the 3‑beat demo *is* the product · every day ends demoable · the **simulator** means the demo works even if hardware dies.

Owners: **HW/FW** = ESP32 + circuit + firmware · **BE/AI** = backend + detection · **FE** = dashboard · **PM** = pitch/glue. See [04](04-tasks-roles.md).

---

## Phase 0 — Pre‑event runway (now → 11 Jul)  *do the risky, slow things early*

| Owner | Task | Done when |
|---|---|---|
| HW/FW | **Buy** ESP32, SCT‑013‑000, 33Ω + 2×10kΩ resistors, 10µF cap, breadboard, lamp, hair‑dryer | parts in hand |
| HW/FW | **Signal‑conditioning circuit** (burden + 1.65V bias + cap) + read CT **safely** (no negative volts to ADC) | stable RMS current on serial |
| HW/FW | **Calibrate** with a known load (calibration factor ≈ turns/burden ≈ 60.6 @33Ω) | reading matches a reference within ±5% |
| BE/AI | **Strict API Contract** + FastAPI `/ingest` + Redis + Celery skeleton (`docker-compose up`) | posting a sample returns 200 |
| BE/AI | **Synthetic dataset + train tech‑loss regressor + IsolationForest** | `ml/artifacts/*.pkl` load at boot |
| FE | Dashboard skeleton (map + one transformer card + WS) | shows a live reading |
| PM | Read the **official rubric**; draft the problem story + slide skeleton | 1‑pager |

*If hardware slips, the simulator ([04](04-tasks-roles.md) S‑tasks) fully substitutes — Phase 1+ do not block on it.*

## Phase 1 — On‑site build (~96 h)

### H0–4 · Kickoff → *prod/local stack up*
Confirm rubric + the 3‑beat demo; freeze the contract; `docker-compose up` green; edge (or simulator) posts one reading that lands on the dashboard.

### H4–28 · Day 1 — Ingest loop → *checkpoint: live normal readings*
| Owner | Task |
|---|---|
| HW/FW | Edge posts real `i_rms/p/pf/freq` every 1 s per the contract |
| BE/AI | `/ingest` validation + persist + Redis enqueue; `/meters/reading`; WS `edge_reading` |
| FE | Map + transformer detail + live power chart |
| BE/AI | Seed transformers + registered meters |

**Accept:** lamp on → dashboard shows live power, verdict **NORMAL**.

### H28–52 · Day 2 — Balance + baseline → *checkpoint: NORMAL & TECHNICAL beats*
| Owner | Task |
|---|---|
| BE/AI | **Energy‑balance** + **tech‑loss regressor** wired into the Celery worker; `residual_w` |
| BE/AI | Decision → `NORMAL` vs `TECHNICAL_LOSS`; verdicts persisted + WS |
| HW/FW | `temp_c` into payload (sensor or sim); "hot‑air" raises it |
| FE | Verdict badge + loss numbers + baseline line on chart |

**Accept:** blow hot air → verdict flips to **TECHNICAL_LOSS (weather‑adjusted)**, *no* false alarm.

### H52–76 · Day 3 — Theft + XAI → *checkpoint: the full 3‑beat aha*
| Owner | Task |
|---|---|
| BE/AI | **Harmonics/PF** + **anomaly** detectors; fusion → `NTL_THEFT_SUSPECTED` + `theft_estimate_w` + **XAI** |
| FE | **Red critical alert**, XAI "why" panel, theft watts, feeder/phase; alert list + status buttons |
| HW/FW | Hair‑dryer on the **unregistered** outlet reliably triggers it |
| PM | First timed full run; note stalls |

**Accept:** the [Verification](#verification) test passes for all three scenarios.

### H76–88 · Day 4a — Polish → *demo bulletproof*
Rich seed (a city of transformers, a few already "red"); deterministic demo; error/empty states; **record the fallback video**; ⭐ optional HMAC on the contract / MQTT hop if green.

### H88–96 · Day 4b — Pitch + buffer → *timed < 3 min, frozen*
Finalize the deck + 90 s demo script ([05](05-demo-pitch.md)); rehearse ≥3× on the venue network; assign who narrates / who triggers; **code freeze**; buffer.

---

## Verification (definition of done)  {#verification}

Run on the deployed/local stack (hardware **or** simulator):
1. Lamp/normal load → dashboard **NORMAL**, loss ≈ 0.
2. Raise temperature (hot air / `sim technical`) → **TECHNICAL_LOSS**, baseline visibly rises, **no theft alarm**. *(false‑positive killer)*
3. Add unregistered load (hair‑dryer / `sim theft`) → within seconds **NTL_THEFT_SUSPECTED**, device **red**, with `theft_estimate_w`, correct severity, and an **XAI "why"** (residual vs baseline + PF/THD).
4. Set the alert status (dispatched) → it updates + persists.
5. **Fallback:** same three beats play from the simulator and from the recorded video (no live hardware needed).

**Smoke tests:** contract rejects a malformed payload (422) · worker computes residual on a known sample (unit test) · WS delivers a verdict to a client · dashboard renders a red alert.

## Contingency ladder (cut in this order)
1. Drop ⭐ HMAC/MQTT polish. 2. Harmonic 1D‑CNN → PF/THD rules. 3. Regressor → temperature‑indexed lookup table. 4. Real hardware → simulator + recorded video. **Never cut:** the 3 beats + the XAI panel.
