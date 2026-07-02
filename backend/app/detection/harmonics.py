"""Step 3 - Harmonic / power-factor theft signal.

Illegal direct-hooks and unregistered heavy loads distort the current waveform
(high THD) and drag the power factor down. This is evidence independent of the
energy math, so it *confirms* a balance anomaly.
"""
from __future__ import annotations


def _clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


def theft_signature_score(power_factor: float, thd_i_pct: float,
                          healthy_pf: float, thd_alert_pct: float) -> float:
    """0 = clean waveform, 1 = strong illegal-load signature."""
    pf_term = _clamp((healthy_pf - power_factor) / max(healthy_pf, 1e-6))
    thd_term = _clamp((thd_i_pct - thd_alert_pct) / 20.0)  # ~20% THD over the alert = full
    return _clamp(0.6 * pf_term + 0.4 * thd_term)
