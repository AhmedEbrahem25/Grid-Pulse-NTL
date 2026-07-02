"""Step 5 - Decision fusion + Explainable AI.

Combines the energy balance, the multi-factor AI technical-loss baseline, and the
harmonic / anomaly signals into an explainable verdict:
NORMAL | TECHNICAL_LOSS | NTL_THEFT_SUSPECTED.

Per ss.md, the verdict exposes a **theft probability %** and a **reasons
checklist** (Energy imbalance / Expected loss exceeded / PF dropped / THD
increased / Load outside normal pattern) so the UI can show *why*, not just *what*.
"""
from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import List

from ..config import settings
from ..contract import EdgePayload
from . import anomaly, energy_balance, harmonics, technical_loss


def _clamp(x, lo=0.0, hi=1.0):
    return max(lo, min(hi, x))


def run_detection(payload: EdgePayload, transformer: dict,
                  registered_load_w: float, recent_loads: List[float]) -> dict:
    ph = payload.measurement.phases
    load_w = payload.total_active_w()
    current_a = sum(p.i_rms_a for p in ph)
    voltage_v = next((p.v_rms_v for p in ph if p.v_rms_v), 230.0)
    temp_c = payload.env.temp_c if payload.env else None
    dt = datetime.fromtimestamp(payload.ts, tz=timezone.utc)
    rated_kva = float(transformer.get("rated_kva", 400))
    pf = payload.worst_power_factor()
    thd = payload.max_thd()

    feats = {"load_w": load_w, "temp_c": temp_c, "hour": dt.hour, "dow": dt.weekday(),
             "voltage_v": voltage_v, "current_a": current_a, "rated_kva": rated_kva}

    measured_loss = energy_balance.measured_loss_w(load_w, registered_load_w)
    expected_now = technical_loss.expected_loss_w(feats)
    expected_nominal = technical_loss.expected_loss_at_nominal(feats)
    residual = measured_loss - expected_now
    pct_over_expected = ((measured_loss / expected_now - 1.0) * 100.0) if expected_now > 1 else 0.0

    sig = harmonics.theft_signature_score(pf, thd, settings.healthy_pf, settings.thd_alert_pct)
    anom = anomaly.anomaly_score(load_w, dt.hour, residual, recent_loads)
    margin = settings.residual_alert_w

    # --- reasons checklist (ss.md) ---
    reasons = [
        {"label": "Energy imbalance", "met": residual > margin,
         "detail": f"unaccounted {residual:+.0f} W (margin {margin:.0f} W)"},
        {"label": "Expected loss exceeded", "met": measured_loss > 1.15 * expected_now and residual > margin,
         "detail": f"actual {pct_over_expected:+.0f}% vs AI baseline"},
        {"label": "Power factor dropped", "met": pf < settings.healthy_pf,
         "detail": f"{pf:.2f} (healthy >= {settings.healthy_pf:.2f})"},
        {"label": "THD increased", "met": thd > settings.thd_alert_pct,
         "detail": f"{thd:.1f}% (alert > {settings.thd_alert_pct:.0f}%)"},
        # A temporal outlier only points to theft when it's an *excess* draw --
        # a sudden load drop is anomalous but not theft. Gate on positive residual
        # so NORMAL/technical never show this tick after a theft replay.
        {"label": "Load outside normal pattern", "met": anom > 0.5 and residual > 0,
         "detail": f"anomaly score {anom:.2f}"},
    ]

    # --- classify ---
    theft = (residual > margin and (sig > 0.30 or anom > 0.50)) or (residual > 2 * margin)
    heat_inflated = expected_now > 1.15 * max(expected_nominal, 1e-6)

    if theft:
        label = "NTL_THEFT_SUSPECTED"
    elif heat_inflated and measured_loss > 0.5 * max(expected_nominal, 1.0):
        label = "TECHNICAL_LOSS"
    else:
        label = "NORMAL"

    theft_estimate = max(0.0, residual) if theft else 0.0
    frac = theft_estimate / max(load_w, 1.0)

    if label == "NTL_THEFT_SUSPECTED":
        if frac > 0.25 or pf < 0.75:
            severity = "critical"
        elif frac > 0.10:
            severity = "high"
        elif frac > 0.05:
            severity = "medium"
        else:
            severity = "low"
        # Confidence grows with the strength of the unexplained residual and is
        # boosted when the two *independent* detectors (harmonics, temporal
        # anomaly) corroborate it. Three signals agreeing = high confidence.
        residual_strength = _clamp(residual / (2 * margin))
        confidence = _clamp(0.50 + 0.30 * residual_strength + 0.14 * sig + 0.10 * anom, 0.55, 0.99)
    elif label == "TECHNICAL_LOSS":
        severity = "low"
        confidence = _clamp(expected_now / max(expected_nominal, 1e-6) - 1.0, 0.55, 0.95)
    else:
        severity = "info"
        confidence = 0.9

    theft_probability = round(confidence * 100) if label == "NTL_THEFT_SUSPECTED" else 0

    return {
        "transformer_id": payload.site.transformer_id,
        "ts": payload.ts,
        "phase": payload.primary_phase(),
        "label": label,
        "confidence": round(confidence, 3),
        "theft_probability": theft_probability,
        "measured_loss_w": round(measured_loss, 1),
        "tech_loss_expected_w": round(expected_now, 1),
        "residual_w": round(residual, 1),
        "pct_over_expected": round(pct_over_expected, 1),
        "theft_estimate_w": round(theft_estimate, 1),
        "severity": severity,
        "explanation": _explain(label, measured_loss, expected_now, residual,
                                pf, thd, theft_estimate, theft_probability, reasons),
        "reasons": reasons,
        "features_used": technical_loss.FEATURES,
        "status": "open",
        "created_at": int(time.time()),
    }


def _explain(label, measured, expected, residual, pf, thd, theft_w, prob, reasons) -> dict:
    if label == "NTL_THEFT_SUSPECTED":
        summary = f"Theft probability {prob}% - ~{theft_w/1000:.2f} kW unaccounted beyond natural loss"
    elif label == "TECHNICAL_LOSS":
        summary = f"Technical loss ~{measured:.0f} W - explained by temperature/load (no theft)"
    else:
        summary = "Normal - energy balance holds"
    factors = [
        {"signal": "residual vs AI baseline",
         "detail": f"measured {measured:.0f} W vs expected {expected:.0f} W (residual {residual:+.0f} W)",
         "weight": 0.5},
        {"signal": "power factor", "detail": f"{pf:.2f} (healthy >= {settings.healthy_pf:.2f})", "weight": 0.3},
        {"signal": "current THD", "detail": f"{thd:.1f}% (alert > {settings.thd_alert_pct:.0f}%)", "weight": 0.2},
    ]
    recommended = "dispatch field inspection" if label == "NTL_THEFT_SUSPECTED" else "monitor"
    return {"summary": summary, "theft_probability": prob,
            "reasons": [r for r in reasons if r["met"]], "factors": factors, "recommended": recommended}
