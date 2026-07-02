# Grid‑Pulse NTL — Detection & AI (the hero)

*Part of the plan set · see also: [01-architecture](01-architecture.md) (data model & API) · [05-demo-pitch](05-demo-pitch.md) (on stage)*

> The differentiator is **not** "we measure the difference." It's **"our AI knows how much loss is *normal right now* (heat/load/time), so the leftover is real theft."** That kills false positives and wins the room.

---

## 1. Pipeline

```
EdgeReading (+ registered meter reads) ──▶
   ① Energy Balance      → measured_loss_w
   ② AI Technical-Loss   → tech_loss_expected_w      (regression on temp/load/time)
   residual_w = measured_loss_w − tech_loss_expected_w
   ③ Harmonics/PF        → theft_signature_score      (waveform distortion)
   ④ Temporal Anomaly    → anomaly_score              (consumption-curve outlier)
                    ▼
   ⑤ Decision fusion → label · confidence · theft_estimate_w · severity · XAI
```

Runs in the **Celery worker** (`backend/app/detection/`). Steps ①②③④ are independent → easy to parallelize and to test.

## 2. ① Energy Balance (`detection/energy_balance.py`)

Over each interval, for a transformer:

```
measured_loss_w = P_transformer_out − Σ P_registered_meters
```

- `P_transformer_out` = active power from the Edge Node (the CT on the feeder).
- `Σ P_registered_meters` = sum of *registered/legal* consumption in that window.
- A large positive `measured_loss_w` = energy leaving the transformer that **nobody is paying for** → *candidate* theft **or** natural technical loss. Step ② decides which.

**POC mapping:** CT (total feeder) = `P_transformer_out`; the **lamp** = the one *registered* load (`Σ P_registered_meters`); the **hair‑dryer on an unregistered outlet** = the unpaid draw that inflates `measured_loss_w`.

## 3. ② AI Technical‑Loss Baseline — the false‑positive killer (`detection/technical_loss.py`)

**Why:** cable/transformer losses are real and **rise with temperature and load** (I²R, and R rises with heat). A fixed loss % alarms all summer. So we *predict* the expected natural loss.

- **Model:** `RandomForestRegressor` (or `XGBoost`) — small, trains in seconds.
- **Features (multi‑factor, per ss.md — *not* temperature alone):** `load_w`, `temp_c`, `hour`, `day_of_week`, `voltage_v`, `current_a`, `rated_kva`. The more real inputs the model weighs, the more credible it is to judges (a temperature‑only model reads as simplistic).
- **Target:** expected technical loss `tech_loss_expected_w` (from physics‑seeded synthetic data — see §8).
- **Output:** `tech_loss_expected_w`, and the **residual**:

```
residual_w = measured_loss_w − tech_loss_expected_w
```

If `residual_w` is within margin → **TECHNICAL_LOSS** (explained, no alarm). If it blows past margin → theft candidate. **This is the "hot‑air" demo beat.**

## 4. ③ Harmonic / Power‑Factor Signal (`detection/harmonics.py`)

Illegal direct‑hooks and unregistered heavy loads (workshops, motors, mining rigs) **distort the AC waveform** and **drop the power factor** — a fingerprint separate from the energy math.

- Edge ships `thd_i_pct`, `power_factor`, and optional per‑harmonic magnitudes (FFT bins).
- **POC logic (rules):** `theft_signature_score` rises when `thd_i_pct` spikes **and** `power_factor` falls below a healthy band **without** a registered industrial customer that would explain it.
- **Stretch (Phase 2):** a **1D‑CNN** classifies the harmonic vector → *legit industrial* vs *illegal bypass* signatures.

## 5. ④ Temporal Anomaly (`detection/anomaly.py`)

- **Model:** `IsolationForest` (stretch: Autoencoder) on the transformer's recent consumption curve + residual history.
- **Catches:** repeating unexplained draws (e.g., **02:00–06:00** brick‑kiln/workshop hooks) that don't match registered meters.
- **Output:** `anomaly_score ∈ [0,1]`.

## 6. ⑤ Decision fusion (`detection/decision.py`)

```
if residual_w ≤ margin(load):        label = NORMAL          # balance holds
elif explained_by_baseline:          label = TECHNICAL_LOSS  # residual small vs expected
else:                                label = NTL_THEFT_SUSPECTED
theft_estimate_w = max(0, residual_w)
confidence = fuse(residual_margin_ratio, theft_signature_score, anomaly_score)   # agreement ⇒ higher
```

`margin(load)` scales with load and the model's uncertainty so small transformers aren't over‑alarmed.

### Severity bands  {#severity}
| theft_estimate_w vs. transformer load | severity |
|---|---|
| within margin | `info` (NORMAL) |
| explained by baseline | `low` (TECHNICAL_LOSS) |
| 5–10 % unexplained | `medium` |
| 10–25 % unexplained | `high` |
| > 25 % **or** PF collapse + harmonic match | `critical` |

## 7. XAI — theft probability + reasons checklist on every Verdict (per ss.md)

Don't say "Theft Detected." Show a **probability** and a **checklist of the reasons that fired** — that's what earns trust from judges and inspectors.

```json
{
  "label": "NTL_THEFT_SUSPECTED",
  "theft_probability": 94,
  "measured_loss_w": 3400, "tech_loss_expected_w": 324, "residual_w": 3076, "pct_over_expected": 951,
  "reasons": [
    {"label": "Energy imbalance",            "met": true, "detail": "unaccounted +3076 W (margin 400 W)"},
    {"label": "Expected loss exceeded",      "met": true, "detail": "actual +951% vs AI baseline"},
    {"label": "Power factor dropped",        "met": true, "detail": "0.66 (healthy ≥ 0.92)"},
    {"label": "THD increased",               "met": true, "detail": "22% (alert > 10%)"},
    {"label": "Load outside normal pattern", "met": true, "detail": "anomaly 0.83"}
  ],
  "explanation": {"summary": "Theft probability 94% — ~3.08 kW unaccounted beyond natural loss",
                  "recommended": "dispatch field inspection"}
}
```

The UI renders **"Theft Probability 94%"** + the ✓/○ checklist (not a bare alarm). `theft_probability` and `reasons` come straight from `decision.py`; the dashboard's assessment panel binds to them directly.

## 8. Training pipeline (offline, `ml/`)

1. `generate_dataset.py` — **physics‑seeded synthetic data**: `tech_loss = k·I²·R(temp) + transformer_core_loss`, swept over temp/load/time (+ noise). Optionally inject labeled theft rows for the anomaly/harmonic parts.
2. `train.py` — fit the **tech‑loss regressor** (features §3) and the **IsolationForest**; save to `ml/artifacts/` (`tech_loss.pkl`, `iforest.pkl`, `meta.json` with margins/PF bands).
3. Backend loads artifacts at boot. Retraining is minutes — safe to iterate.

*Synthetic is fine and defensible:* say so, and note the model retrains on real utility data in production.

## 9. Demo scenarios (deterministic — `POST /sim/scenario`)

| scenario | injected | ① balance | ② baseline | ③/④ | verdict |
|---|---|---|---|---|---|
| `normal` | lamp only | loss ≈ 0 | low | quiet | **NORMAL** |
| `technical` | raise `temp_c` (hot air) | loss ↑ | **expected ↑ to match** | quiet | **TECHNICAL_LOSS** (no alarm) |
| `theft` | +hair‑dryer on unregistered outlet | loss ↑↑ | expected stays | PF↓, THD↑, anomaly↑ | **NTL_THEFT_SUSPECTED** (red) |

## 10. Graceful degradation

- **Regressor late?** Use a temperature‑indexed loss **lookup table** — still separates heat‑loss from theft, still demos.
- **No harmonics from edge?** Energy‑balance + baseline alone carries the three beats; PF/THD is the bonus.
- Always keep the **XAI panel** — cheap, decisive.

## 11. Phase‑2 AI (pitch as roadmap, don't build)

1D‑CNN harmonic classifier · **TinyML on‑device** inference (send only when theft found → −99% bandwidth) · theft‑location triangulation across feeders · load‑forecasting to pre‑empt overload/load‑shedding · federated learning across regions.
