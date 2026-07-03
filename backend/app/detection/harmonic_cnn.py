"""Harmonic-signature classifier (the "Phase-2 AI", made real).

Classifies the current-harmonic spectrum as clean / legit_industrial /
illegal_bypass using a tiny 1D-CNN (ml/train_harmonics.py). This is what lets
the system tell a *registered* high-THD factory apart from an *illegal* hook —
so a naive THD/PF rule doesn't cry theft on legitimate industrial load.

Degrades gracefully: if torch or the artifact is missing, a transparent
rule-of-thumb (from THD + power factor) stands in, and the demo is unaffected.
"""
from __future__ import annotations

import json
import math
import os
from typing import List, Optional

from ..config import settings

NBINS = 14
HARMONIC_ORDERS = list(range(2, 2 + NBINS))   # h = 2 .. 15
CLASSES = ["clean", "legit_industrial", "illegal_bypass"]

_model = None
_meta = None
_loaded = False


def _try_load():
    global _model, _meta, _loaded
    if _loaded:
        return
    _loaded = True
    meta_p = os.path.join(settings.artifacts_dir, "harmonic_meta.json")
    pt_p = os.path.join(settings.artifacts_dir, "harmonic_cnn.pt")
    if not (os.path.exists(meta_p) and os.path.exists(pt_p)):
        return
    try:
        import torch
        import torch.nn as nn
        _meta = json.load(open(meta_p))

        class HarmonicCNN(nn.Module):
            def __init__(self):
                super().__init__()
                self.net = nn.Sequential(
                    nn.Conv1d(1, 8, 3, padding=1), nn.ReLU(),
                    nn.Conv1d(8, 16, 3, padding=1), nn.ReLU(),
                    nn.AdaptiveAvgPool1d(1), nn.Flatten(),
                    nn.Linear(16, 24), nn.ReLU(),
                    nn.Linear(24, len(CLASSES)),
                )

            def forward(self, x):
                return self.net(x)

        m = HarmonicCNN()
        m.load_state_dict(torch.load(pt_p, map_location="cpu"))
        m.eval()
        _model = m
    except Exception as e:  # pragma: no cover
        print(f"[harmonic_cnn] model unavailable, using rule fallback: {e}")
        _model = None


_FLOOR = 0.7   # matches the per-bin noise floor the CNN was trained with


def _spectrum(harmonics: Optional[List], thd_pct: float, pf: float) -> List[float]:
    """14-bin spectrum (h=2..15) from the payload's harmonics[] if present,
    otherwise synthesized from scalar THD/PF so it still runs on demo payloads."""
    x = [0.0] * NBINS
    idx = {h: i for i, h in enumerate(HARMONIC_ORDERS)}
    filled = False
    if harmonics:
        for item in harmonics:
            h = getattr(item, "h", None) if not isinstance(item, dict) else item.get("h")
            mag = getattr(item, "mag_pct", None) if not isinstance(item, dict) else item.get("mag_pct")
            if h in idx and mag is not None:
                x[idx[h]] = float(mag)
                filled = True
    if not filled:
        scale = max(0.0, thd_pct) / 20.0
        low_pf = pf < 0.80
        x[idx[3]] = (14 if low_pf else 3) * scale
        x[idx[5]] = (16 if low_pf else 12) * scale
        x[idx[7]] = (9 if low_pf else 7) * scale
        x[idx[9]] = (5 if low_pf else 1) * scale
        x[idx[11]] = (3 if low_pf else 4) * scale
        x[idx[13]] = (2 if low_pf else 3) * scale
    # lift the empty bins to the training noise floor so a sparse edge vector
    # isn't out-of-distribution (which was flipping the classification)
    return [max(v, _FLOOR) for v in x]


def _rule(thd_pct: float, pf: float) -> dict:
    """Transparent fallback: low PF + high THD -> illegal; high THD + healthy PF -> legit."""
    thd_hi = thd_pct >= settings.thd_alert_pct
    if not thd_hi:
        return {"class": "clean", "p_illegal": 0.05, "source": "rule"}
    if pf < 0.80:
        p = min(0.95, 0.5 + (settings.thd_alert_pct and (thd_pct - 10) / 40) + (0.80 - pf))
        return {"class": "illegal_bypass", "p_illegal": round(max(0.5, p), 3), "source": "rule"}
    return {"class": "legit_industrial", "p_illegal": 0.20, "source": "rule"}


def classify(harmonics: Optional[List], thd_pct: float, pf: float) -> dict:
    """-> {class, p_illegal, source}. Always safe to call."""
    _try_load()
    if _model is None or _meta is None:
        return _rule(thd_pct, pf)
    try:
        import torch
        spec = _spectrum(harmonics, thd_pct, pf)
        mean = _meta["mean"]; std = _meta["std"]
        xn = [(spec[i] - mean[i]) / std[i] for i in range(NBINS)]
        t = torch.tensor(xn, dtype=torch.float32).view(1, 1, NBINS)
        with torch.no_grad():
            logits = _model(t)[0]
            ex = [math.exp(float(v)) for v in logits]
            s = sum(ex) or 1.0
            probs = [e / s for e in ex]
        cls = CLASSES[int(max(range(len(probs)), key=lambda i: probs[i]))]
        return {"class": cls, "p_illegal": round(probs[2], 3), "source": "cnn"}
    except Exception:
        return _rule(thd_pct, pf)
