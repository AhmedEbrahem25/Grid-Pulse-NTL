"""Transformer Energy Accounting Layer — an independent evidence module.

Accumulates incoming vs registered energy over a rolling window, compares the
*actual* loss against the AI-predicted *technical* loss, and reports the leftover
**excess loss** as one more piece of evidence for the fusion engine.

It reuses the existing technical-loss regression (technical_loss.expected_loss_w)
and never produces a verdict or an alert by itself — decision.py folds its
`contribution_pct` into the final theft probability (bounded), and the dashboard
renders its numbers. Safe to call with sparse/empty history: it projects the
current reading over the horizon and returns neutral evidence.
"""
from __future__ import annotations

from typing import Dict, List

from ..config import settings


def _clamp(x, lo, hi):
    return max(lo, min(hi, x))


def compute(load_w: float, registered_load_w: float, expected_loss_w: float,
            recent_loads: List[float], horizon_h: float = None,
            model_loaded: bool = False) -> Dict:
    horizon_h = settings.accounting_horizon_h if horizon_h is None else horizon_h
    n = len([v for v in (recent_loads or []) if v is not None])   # only informs confidence

    # Incoming energy at the *current* measured rate over the horizon. (Averaging in the
    # recent normal readings would dilute a theft onset and flip the excess negative.)
    incoming_kwh = load_w / 1000.0 * horizon_h
    registered_kwh = registered_load_w / 1000.0 * horizon_h
    actual_loss_kwh = incoming_kwh - registered_kwh
    expected_technical_kwh = expected_loss_w / 1000.0 * horizon_h
    excess_loss_kwh = actual_loss_kwh - expected_technical_kwh
    excess_loss_pct = (excess_loss_kwh / incoming_kwh * 100.0) if incoming_kwh > 1e-6 else 0.0

    # how much we trust this accounting: data sufficiency + whether the AI model is loaded
    tech_loss_confidence = _clamp(0.60 + 0.25 * min(1.0, n / 60.0) + (0.10 if model_loaded else 0.0), 0.5, 0.95)
    evidence_weight = tech_loss_confidence
    risk_score = _clamp(excess_loss_pct * 5.0, 0.0, 100.0)
    contribution_pct = _clamp(excess_loss_pct * settings.accounting_k, -20.0, 18.0)

    if contribution_pct > 5:
        stance = "supporting"
        reason = "Measured transformer loss significantly exceeded the AI-predicted technical loss."
    elif contribution_pct < -3:
        stance = "rejecting"
        reason = "Measured loss is within the AI-predicted technical loss — energy accounting does not support theft."
    else:
        stance = "neutral"
        reason = "Measured loss matches the expected technical loss; accounting is inconclusive."

    return {
        "incoming_kwh": round(incoming_kwh, 2),
        "registered_kwh": round(registered_kwh, 2),
        "actual_loss_kwh": round(actual_loss_kwh, 2),
        "expected_technical_kwh": round(expected_technical_kwh, 2),
        "excess_loss_kwh": round(excess_loss_kwh, 2),
        "excess_loss_pct": round(excess_loss_pct, 1),
        "tech_loss_confidence": round(tech_loss_confidence, 2),
        "risk_score": round(risk_score),
        "evidence_weight": round(evidence_weight, 2),
        "contribution_pct": round(contribution_pct),
        "applied_contribution": 0,          # set by decision.py after bounded fusion
        "stance": stance,
        "reason": reason,
        "horizon_h": horizon_h,
    }
