"""Synthetic current-harmonic signatures for the 1D-CNN classifier.

Each sample is a 14-bin spectrum — the magnitude (% of the fundamental) of
harmonics h=2..15 of the load current. Three classes carry the whole "AI beats
the naive rule" story:

  0 clean            near-pure sine, PF ~1        (normal residential/feeder)
  1 legit_industrial 5th/7th from PFC motors/drives, corrected PF, *registered*
  2 illegal_bypass   broad 3rd/5th/7th distortion + low PF (hooks, workshops)

A fixed-threshold THD/PF rule confuses classes 1 and 2 (both distort the wave).
The CNN learns the *shape* difference, so a legit factory isn't flagged as theft.

Bin index i -> harmonic order (i + 2). NBINS harmonics starting at the 2nd.
"""
from __future__ import annotations

import numpy as np

NBINS = 14                      # harmonics h = 2 .. 15
HARMONIC_ORDERS = list(range(2, 2 + NBINS))
CLASSES = ["clean", "legit_industrial", "illegal_bypass"]


def _clip(a):
    return np.clip(a, 0.0, 100.0)


def _sample_clean(rng, n):
    x = np.zeros((n, NBINS))
    for i, h in enumerate(HARMONIC_ORDERS):
        x[:, i] = np.abs(rng.normal(1.2 if h % 2 else 0.6, 0.7, n)) / h  # tiny, decaying
    return _clip(x)


def _sample_legit_industrial(rng, n):
    x = np.abs(rng.normal(0.8, 0.5, (n, NBINS)))
    idx = {h: i for i, h in enumerate(HARMONIC_ORDERS)}
    x[:, idx[5]] += rng.uniform(8, 18, n)     # characteristic 6k+/-1 harmonics
    x[:, idx[7]] += rng.uniform(4, 11, n)
    x[:, idx[11]] += rng.uniform(2, 6, n)
    x[:, idx[13]] += rng.uniform(1.5, 5, n)
    x[:, idx[3]] += rng.uniform(0, 3, n)      # low triplen (balanced 3-phase drives)
    return _clip(x)


def _sample_illegal_bypass(rng, n):
    x = np.abs(rng.normal(1.5, 1.0, (n, NBINS)))
    idx = {h: i for i, h in enumerate(HARMONIC_ORDERS)}
    x[:, idx[3]] += rng.uniform(12, 26, n)    # strong triplen from half-wave / clipped loads
    x[:, idx[5]] += rng.uniform(10, 24, n)
    x[:, idx[7]] += rng.uniform(6, 16, n)
    x[:, idx[9]] += rng.uniform(3, 9, n)
    # broad spread across the rest — the "messy" fingerprint
    x += rng.uniform(0, 3, (n, NBINS))
    return _clip(x)


def make_dataset(n: int = 6000, seed: int = 0):
    rng = np.random.default_rng(seed)
    per = n // 3
    X = np.vstack([_sample_clean(rng, per),
                   _sample_legit_industrial(rng, per),
                   _sample_illegal_bypass(rng, n - 2 * per)]).astype("float32")
    y = np.concatenate([np.zeros(per), np.ones(per), np.full(n - 2 * per, 2)]).astype("int64")
    order = rng.permutation(len(y))
    return X[order], y[order]


def spectrum_from_thd(thd_pct: float, pf: float, seed: int | None = None) -> np.ndarray:
    """Approximate a 14-bin spectrum when the edge only reports scalar THD/PF.

    Lets the classifier run on the current demo payloads (which send thd, not the
    full vector). Low PF pushes the shape toward the illegal-bypass fingerprint.
    """
    rng = np.random.default_rng(seed)
    scale = max(0.0, thd_pct) / 20.0
    x = np.zeros(NBINS)
    idx = {h: i for i, h in enumerate(HARMONIC_ORDERS)}
    low_pf = pf < 0.80
    x[idx[3]] = (14 if low_pf else 3) * scale
    x[idx[5]] = (16 if low_pf else 12) * scale
    x[idx[7]] = (9 if low_pf else 7) * scale
    x[idx[9]] = (5 if low_pf else 1) * scale
    x[idx[11]] = (3 if low_pf else 4) * scale
    x[idx[13]] = (2 if low_pf else 3) * scale
    x = x + np.abs(rng.normal(0, 0.4, NBINS))
    return _clip(x).astype("float32")


if __name__ == "__main__":
    X, y = make_dataset()
    print(f"harmonic dataset: X={X.shape} classes={CLASSES} counts={np.bincount(y)}")
