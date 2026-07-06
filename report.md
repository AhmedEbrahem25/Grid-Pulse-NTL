# ⚡ Grid‑Pulse NTL — Full Project Analysis Report

*Kafr El‑Sheikh Hackathon · Autonomous Electricity‑Theft (Non‑Technical Loss) Detector · Egypt B2G*

---

## 1. Executive summary

**Grid‑Pulse NTL** is an AI edge‑to‑cloud system that detects electricity theft on the distribution grid and — crucially — distinguishes *real theft* from the *natural* energy loss caused by heat and load. That separation is the entire moat: naive "meter‑difference" alarms drown operators in false positives during an Egyptian summer; this system uses an AI baseline to explain away natural loss and flags only the **unexplained, corroborated excess**.

- **Problem size:** ~30 billion EGP/year lost to theft in Egypt; worsens load‑shedding (تخفيف الأحمال).
- **Verdicts:** `NORMAL` · `TECHNICAL_LOSS` · `NTL_THEFT_SUSPECTED`, each with a **Theft Probability %** and a **5‑reason checklist** (Explainable AI).
- **Status:** Demo‑verified live in Docker. Theft beat classifies at **94% confidence / 5‑of‑5 reasons / ~3.08 kW unaccounted**.
- **Eval (held‑out synthetic, 600 scenarios):** theft **precision 1.00**, recall 0.78, F1 0.88, **0 false positives**, **0% false alarms on legitimate industrial load**, Brier 0.053 (calibrated).

The repo is unusually complete for a hackathon: working code + trained models + eval harness + firmware + simulator + dashboard + three pitch decks (web + PPTX + PDF) + a business/finance model + a competitive landscape + a real‑deployment engineering story.

---

## 2. What the codebase actually contains

| Area | Files | Lines | State |
|---|---|---:|---|
| **Backend** (FastAPI + detection) | 19 `.py` | 1,508 | Working, tested |
| **ML** (train/eval/generate) | 5 `.py` + artifacts | 401 | Trained, evaluated |
| **Firmware** (ESP32) | `.ino` + `config.h` + README | 184 | Written, not compiled here |
| **Dashboard** | single‑file `index.html` | 556 | Served at `/` |
| **Simulator** | `simulate.py` | — | No‑hardware demo stream |
| **Contracts** | `edge_telemetry.schema.json` + README | — | Strict API contract |
| **Plan docs** | `plan/00`–`06` | 7 docs | Strategy → runbook |
| **Pitch / Business** | 3 web pages + 3 PPTX + 3 PDF | — | Rendered |
| **Deployment / Competition** | `deployment/`, `competition/` HTML | — | Engineering + market story |

**Trained artifacts present:** `tech_loss.pkl` (RandomForest regressor), `iforest.pkl` (IsolationForest), `harmonic_cnn.pt` (PyTorch 1D‑CNN), `calibrator.pkl` (isotonic), plus `meta.json`, `harmonic_meta.json`, `eval_report.json`.

---

## 3. Architecture

```
CT sensor (SCT-013) → ESP32 edge node (EmonLib RMS + FFT → I·P·PF·THD)
   → JSON contract over Wi-Fi/LoRaWAN
   → FastAPI /ingest (strict Pydantic validation, zero-trust)
   → Redis queue → Celery worker(s): energy-balance → tech-loss AI
                    → accounting → harmonics(1D-CNN) → anomaly → decision
   → store + WebSocket push → single-file ops dashboard (map · probability · reasons · Wh)
```

**Key design decision:** the **edge does the DSP** (RMS, power factor, FFT/THD), so the system ships *features*, not raw waveforms — tiny payloads that scale to thousands of transformers.

**Stack rationale:** ESP32/C++ (cheap, Wi‑Fi, does DSP locally) · FastAPI + Pydantic (validates the Strict Contract) · Redis (burst absorption) · Celery (async inference / real microservices story) · scikit‑learn + PyTorch · FastAPI WebSocket (live red alert) · single‑file dashboard · `docker‑compose up` (one command on stage).

`INLINE_DETECTION=true` (default) runs detection inside the API for demo simplicity; set `false` to route through Celery over Redis pub/sub — the same code, two deployment stories.

---

## 4. The detection pipeline (the core IP)

Six steps fuse into one explainable verdict. Verified against `backend/app/detection/decision.py`:

| Step | File | Role |
|---|---|---|
| ① Energy balance | `energy_balance.py` (10 L) | `measured_loss = P_transformer_out − ΣP_registered_meters` |
| ② Technical‑loss AI | `technical_loss.py` (70 L) | Predicts **expected natural loss** → **residual = measured − expected** is what matters |
| ③ Energy accounting | `accounting.py` (70 L) | Rolling‑window kWh actual vs expected → **bounded** excess‑loss evidence (never alarms alone) |
| ④ Harmonic 1D‑CNN + PF | `harmonic_cnn.py` (126 L) · `harmonics.py` (19 L) | Classifies spectrum: `clean` / `legit_industrial` / `illegal_bypass`; **degrades to a THD/PF rule if torch absent** |
| ⑤ Temporal anomaly | `anomaly.py` (47 L) | IsolationForest `decision_function` catches repeating unexplained draws |
| ⑥ Decision fusion | `decision.py` (187 L) | Calibrated label + probability + theft estimate + reasons + XAI |

**Classification logic (verified):**
```python
theft = (residual > margin and (sig > 0.30 or anom > 0.50)) or (residual > 2*margin)
if legit_ind and residual < 3*margin:   theft = False   # 1D-CNN clears registered factories
```
The CNN is genuinely **load‑bearing**: a legitimate high‑THD factory (registered) does not trip the alarm, while a clear excess (>3× margin) still trips regardless. THD only counts as theft when the harmonic *shape* is illegal.

**Confidence formula** rewards multi‑detector corroboration (three independent signals agreeing → high confidence):
```python
confidence = clamp(0.50 + 0.30*residual_strength + 0.14*sig + 0.10*anom, 0.55, 0.99)
```

**Accounting layer** folds a *bounded* adjustment (`applied ∈ [−15, +5]`) into the probability — it damps borderline/false‑positive cases without ever flipping the label or the 5‑reason checklist. A brazen theft stays ~94%; a weak/ambiguous one is damped down.

**The 5‑reason checklist (Explainable AI):**
1. Energy imbalance — unaccounted watts beyond the margin.
2. Expected loss exceeded — actual % over the AI baseline.
3. Power factor dropped — below the healthy PF threshold.
4. THD increased — gated on an *illegal* harmonic signature (not a legit‑industrial one).
5. Load outside normal pattern — temporal anomaly, gated on a *positive* residual (a load drop is never theft).

---

## 5. The model is genuinely multi‑factor (not temperature‑only)

A reviewer warned that a temperature‑only model reads as simplistic. The RandomForest regressor is trained on **7 features over 8,000 physics‑seeded rows** (`tech_loss ≈ k·I²·R(temp) + core_loss`). Learned importances (`ml/artifacts/meta.json`) prove **load leads, not temperature**:

| Feature | Importance |
|---|---:|
| `load_w` | **0.578** |
| `temp_c` | 0.270 |
| `current_a` | 0.148 |
| `hour` | 0.002 |
| `dow` | 0.001 |
| `voltage_v` | 0.001 |
| `rated_kva` | 0.001 |

A separate **1D‑CNN** (14 harmonic bins, h=2…15) sorts the current spectrum into `clean · legit_industrial · illegal_bypass`.

---

## 6. Evaluation (honest, synthetic)

Held out **600 labeled scenarios** across 4 classes, scoring the **full fused pipeline** (`ml/artifacts/eval_report.json`):

| Metric | Value | Meaning |
|---|---:|---|
| Theft precision | **1.00** | When it fires, it's right — **0 false positives** |
| Theft recall | 0.783 | Catches 123 of 157 thefts (stealthy small hooks are genuinely hard) |
| Theft F1 | 0.879 | Balanced |
| False‑alarm on industrial load | **0.0%** | 🏆 The 1D‑CNN never mistakes a factory for a hook |
| Brier (calibrated) | 0.058 → **0.053** | Probabilities are calibrated, not just ranked |

Confusion: `TP 123 · FP 0 · FN 34 · TN 443`. Per‑class theft‑flag counts confirm normal/technical/industrial all flag **0** thefts (141 / 163 / 139 scenarios respectively), and theft flags 123 of 157.

**Honesty note built into the docs:** this is synthetic held‑out data; recall <1 is disclosed, not hidden.

---

## 7. The API contract (zero‑trust)

Canonical schema: `contracts/edge_telemetry.schema.json`, mirrored 1:1 by `backend/app/contract.py` (Pydantic, `extra="forbid"`). Strong validation: regex‑constrained IDs (`GP-EDGE-…`, `TX-…`), bounded ranges (current ≤5000 A, PF 0–1, freq 45–65 Hz, ≤3 phases, ≤16 harmonics), timestamp floor, optional HMAC `sig` field. Verified behavior: `/ingest` returns **401** (bad token) and **422** (malformed body).

**Endpoints:**

| Method & path | Purpose |
|---|---|
| `POST /ingest` | Edge payload (must match schema) → `{accepted, reading_id}` |
| `POST /meters/reading` | Registered meter reads |
| `GET /transformers` | List + latest verdict |
| `GET /transformers/{id}` | Detail + recent readings/verdicts |
| `GET /transformers/{id}/history` | Time‑series for dashboard charts |
| `GET /verdicts?label&severity&status` | Verdicts, newest first |
| `POST /verdicts/{id}/status` | Update verdict status |
| `GET /leads` | Ranked theft leads (inspection queue) |
| `POST /sim/scenario` | Inject `normal \| technical \| theft \| industrial` |
| `POST /sim/reset` | Reset demo state |
| `GET /healthz` | Health check |
| `WS /ws/stream` | Events: `edge_reading` · `verdict` · `transformer_status` · `reset` |

---

## 8. Supporting engineering (the "we thought about reality" layer)

- **Firmware** (`esp32_edge_node`): EmonLib `calcVI` + ZMPT101B voltage channel (GPIO35) + arduinoFFT for real THD & `harmonics[]`. SCT‑013‑000 conditioning documented (33 Ω burden, 1.65 V bias, 10 µF cap; cal factor ≈ 60.6).
- **Real deployment story** (`deployment/index.html`): non‑invasive, LV‑side‑only retrofit into a sealed distribution kiosk/RMU — 3 Rogowski coils on LV busbars, ESP32 in IP65 enclosure, antenna routed outside the Faraday cage. No MV contact, no galvanic connection, zero outage, reversible. This is the standout differentiator.
- **Persistence:** SQLModel + SQLite, write‑through, restored on boot; verdicts survive `docker compose restart`.
- **Always‑on stream** + **theft alerts** (webhook/Telegram, config‑gated) + **replay‑safe demo** + **Reset Demo**.
- **Dashboard:** offline‑capable map (vendored Leaflet), loss history charts, inspection queue, energy‑accounting card with stance chips.

---

## 9. Business & go‑to‑market

- **Model:** B2G SaaS + Hardware‑as‑a‑Service to distribution companies / Ministry of Electricity.
- **Pricing:** % of recovered energy **or** per‑transformer subscription; ROI **< 1 month per kiosk**.
- **TAM:** ~30B EGP/yr; recovering 10% ≈ 3B EGP.
- **Full financial model** (`business/index.html`): 3 revenue streams (hardware EGP 6k/node · SaaS EGP 300/node/mo · 15% recovery‑share), hardware BOM (prototype ~EGP 1k vs production ~EGP 6k), LTV/CAC ~8×, 5‑yr model (breakeven Y3, Y5 rev ~EGP 605M), EGP 30M (~$625K) seed ask.
- **Competitive analysis** (`competition/index.html`): positioned as the *only* low‑CapEx + explainable + no‑AMI‑required approach; complements AMI, substitutes where none exists.
- **Decks:** pitch (petrol/cyan), formal prospectus (navy/serif), business — each as web + PPTX + PDF.

---

## 10. Strengths, risks & recommendations

**Strengths**
- The false‑positive‑killer thesis is real, implemented, and evaluated — not a slide.
- Explainability (probability + reasons + XAI factors) is baked into every verdict.
- Genuine multi‑factor model + load‑bearing CNN, not a temperature threshold.
- End‑to‑end completeness: firmware → API → AI → dashboard → decks → deployment engineering.

**Risks / gaps to be honest about**
1. **All evaluation is synthetic.** The single most important next step is real (or public utility) data. State this proactively to judges.
2. **Name collision** — "Grid‑Pulse" collides with an unrelated reference project. Recommend a distinct final name (AmperGuard / رقيب‑Rakib / WattWatch).
3. **Firmware not compiled/HIL‑tested here** — it's written but unproven on silicon.
4. **Single‑file dashboard + SQLite** are demo‑grade by design; production needs a real DB and hardened frontend.
5. Repo hygiene: `bash.exe.stackdump`, `.env` committed, and a modified `.codeboarding` log are lingering — worth a cleanup before sharing.

**Recommended next moves:** lock a final product name → get any slice of real feeder data → compile/HIL‑test one ESP32 node → tighten repo hygiene (remove `.env`, stackdump) before publishing.

---

## 11. Quickstart (reference)

```bash
cp .env.example .env
docker-compose up --build         # api :8000 + redis + celery worker
python ml/train.py                # optional — physics fallback works without a trained model
# open http://localhost:8000, pick a transformer, drive the demo bar
python simulator/simulate.py      # optional live telemetry stream
```

Verify the three beats + contract rejects:
```bash
docker-compose exec api python backend/tests/test_detection.py
```

---

*Report generated from a direct audit of the repository (code, trained artifacts, eval report, contract, and docs).*
