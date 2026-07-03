"""Evaluate the full detection pipeline on a labeled held-out set (B4).

Builds realistic normal / technical / legit-industrial / theft telemetry, runs
each row through the *actual* backend decision (energy balance -> AI baseline ->
harmonics 1D-CNN -> anomaly -> fusion), and reports theft precision / recall /
F1, the confusion matrix, and the Brier score of the theft probability. Also
fits an isotonic calibrator and reports the calibrated Brier.

Run inside the api container (all deps present):
    python ml/evaluate.py
Writes ml/artifacts/eval_report.json (+ artifacts/calibrator.pkl).
"""
from __future__ import annotations

import json
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
from app.contract import EdgePayload            # noqa: E402
from app.detection.decision import run_detection  # noqa: E402

ART = os.path.join(os.path.dirname(__file__), "artifacts")
os.makedirs(ART, exist_ok=True)
BASE_REG = 6800.0
seq = 9000


def _payload(tid, total, pf, thd, temp, harmonics):
    global seq
    seq += 1
    phase = {"phase": "single", "i_rms_a": round(total / 230, 1), "v_rms_v": 230.0,
             "p_active_w": total, "s_apparent_va": round(total / max(pf, 0.01), 1),
             "power_factor": pf, "freq_hz": 49.98, "thd_i_pct": thd, "harmonics": harmonics}
    return EdgePayload(schema_version="1.0", device_id="GP-EDGE-EVAL01", firmware="1.0.0",
                       ts=int(time.time()), seq=seq,
                       site={"transformer_id": tid, "feeder_id": "F-03", "lat": 31.1, "lng": 30.9},
                       measurement={"window_ms": 1000, "phases": [phase]},
                       env={"temp_c": temp, "humidity_pct": 50.0})


H_NORMAL = [{"h": 3, "mag_pct": 2.0}, {"h": 5, "mag_pct": 2.5}]
H_LEGIT = [{"h": 5, "mag_pct": 14.0}, {"h": 7, "mag_pct": 8.0}, {"h": 11, "mag_pct": 4.0}]
H_ILLEGAL = [{"h": 2, "mag_pct": 4.0}, {"h": 3, "mag_pct": 18.0}, {"h": 4, "mag_pct": 4.0},
             {"h": 5, "mag_pct": 20.0}, {"h": 7, "mag_pct": 13.0}, {"h": 9, "mag_pct": 8.0},
             {"h": 11, "mag_pct": 6.0}, {"h": 13, "mag_pct": 5.0}]


def make_case(rng, cls):
    """-> (payload, registered_w, is_theft)."""
    tid = "TX-KFS-0456"
    if cls == "normal":
        total = rng.uniform(6600, 6950)
        return _payload(tid, total, rng.uniform(0.95, 0.99), rng.uniform(3, 6), rng.uniform(20, 34), H_NORMAL), BASE_REG, 0
    if cls == "technical":
        total = rng.uniform(6900, 7200)
        return _payload(tid, total, rng.uniform(0.96, 0.98), rng.uniform(4, 7), rng.uniform(42, 48), H_NORMAL), BASE_REG, 0
    if cls == "industrial":                              # registered factory: high THD, legit
        total = rng.uniform(8000, 9500)
        reg = total - rng.uniform(0, 700)                # metering lag -> small residual (tests false-alarm suppression)
        return _payload(tid, total, rng.uniform(0.90, 0.94), rng.uniform(16, 24), rng.uniform(24, 34), H_LEGIT), reg, 0
    # theft: unregistered excess draw, illegal signature
    if rng.random() < 0.28:                              # stealthy small hook — the genuinely hard case
        total = rng.uniform(7300, 7900); pf = rng.uniform(0.78, 0.86); thd = rng.uniform(14, 20)
    else:                                                # brazen hook
        total = rng.uniform(9600, 12000); pf = rng.uniform(0.60, 0.75); thd = rng.uniform(18, 30)
    return _payload(tid, total, pf, thd, rng.uniform(24, 34), H_ILLEGAL), BASE_REG, 1


def main():
    rng = np.random.default_rng(7)
    transformer = {"id": "TX-KFS-0456", "rated_kva": 400}
    y_true, y_pred, probs = [], [], []
    per_class = {c: {"n": 0, "theft_flag": 0} for c in ["normal", "technical", "industrial", "theft"]}
    classes = ["normal", "technical", "industrial", "theft"]

    for _ in range(600):
        cls = classes[rng.integers(0, 4)]
        payload, reg, is_theft = make_case(rng, cls)
        v = run_detection(payload, transformer, reg, [])
        pred_theft = int(v["label"] == "NTL_THEFT_SUSPECTED")
        y_true.append(is_theft); y_pred.append(pred_theft)
        probs.append((v.get("theft_probability", 0) or 0) / 100.0)
        per_class[cls]["n"] += 1
        per_class[cls]["theft_flag"] += pred_theft

    y_true = np.array(y_true); y_pred = np.array(y_pred); probs = np.array(probs)
    tp = int(((y_pred == 1) & (y_true == 1)).sum())
    fp = int(((y_pred == 1) & (y_true == 0)).sum())
    fn = int(((y_pred == 0) & (y_true == 1)).sum())
    tn = int(((y_pred == 0) & (y_true == 0)).sum())
    precision = tp / (tp + fp) if tp + fp else 1.0
    recall = tp / (tp + fn) if tp + fn else 1.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    brier = float(np.mean((probs - y_true) ** 2))

    # isotonic calibration of the probability (report improvement; artifact saved)
    cal_brier = brier
    try:
        from sklearn.isotonic import IsotonicRegression
        import joblib
        iso = IsotonicRegression(out_of_bounds="clip").fit(probs, y_true)
        cal = iso.predict(probs)
        cal_brier = float(np.mean((cal - y_true) ** 2))
        joblib.dump(iso, os.path.join(ART, "calibrator.pkl"))
    except Exception as e:
        print(f"[eval] calibration skipped: {e}")

    report = {
        "n": int(len(y_true)),
        "theft_precision": round(precision, 3), "theft_recall": round(recall, 3), "theft_f1": round(f1, 3),
        "confusion": {"tp": tp, "fp": fp, "fn": fn, "tn": tn},
        "brier_score": round(brier, 4), "brier_calibrated": round(cal_brier, 4),
        "false_alarm_rate_industrial": round(per_class["industrial"]["theft_flag"] / max(1, per_class["industrial"]["n"]), 3),
        "per_class": per_class,
    }
    json.dump(report, open(os.path.join(ART, "eval_report.json"), "w"), indent=2)

    print("\n=== Grid-Pulse NTL — detection eval (held-out) ===")
    print(f"  n = {report['n']}   theft: P={precision:.3f}  R={recall:.3f}  F1={f1:.3f}")
    print(f"  confusion  tp={tp} fp={fp} fn={fn} tn={tn}")
    print(f"  Brier (probability): {brier:.4f}   isotonic-calibrated: {cal_brier:.4f}")
    print(f"  legit-industrial false-alarm rate: {report['false_alarm_rate_industrial']:.3f}  "
          f"(should be ~0 — the CNN clears legit high-THD load)")
    print(f"  report -> {ART}/eval_report.json\n")


if __name__ == "__main__":
    main()
