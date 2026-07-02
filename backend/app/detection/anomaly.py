"""Step 4 - Temporal anomaly (Isolation Forest).

Flags consumption-curve outliers (e.g., repeated large unexplained draws at 3am).
Uses ml/artifacts/iforest.pkl if present; otherwise returns 0 (neutral) so the
balance + harmonic signals still drive the decision.
"""
from __future__ import annotations

import os
from typing import List

from ..config import settings

_model = None
_loaded = False


def _try_load():
    global _model, _loaded
    if _loaded:
        return
    _loaded = True
    path = os.path.join(settings.artifacts_dir, "iforest.pkl")
    if os.path.exists(path):
        try:
            import joblib
            _model = joblib.load(path)
        except Exception:
            _model = None


def anomaly_score(load_w: float, hour: int, residual_w: float, recent_loads: List[float]) -> float:
    """0 = typical, 1 = strong temporal outlier."""
    _try_load()
    if _model is None:
        return 0.0
    try:
        import numpy as np
        avg = float(np.mean(recent_loads)) if recent_loads else load_w
        x = np.array([[load_w, hour, residual_w, load_w - avg]], dtype=float)
        # decision_function: >0 = inlier, <0 = outlier, with 0 at the model's own
        # contamination boundary. Map so a clean reading sits well below 0.5 and a
        # clear outlier saturates toward 1.
        d = float(_model.decision_function(x)[0])
        return max(0.0, min(1.0, 0.5 - 4.0 * d))
    except Exception:
        return 0.0
