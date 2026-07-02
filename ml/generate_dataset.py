"""Physics-seeded synthetic dataset for the multi-factor technical-loss model.

Feature order MUST match backend/app/detection/technical_loss.py::FEATURES.
Target = natural technical loss (copper loss ~ load, resistance rises with temp),
plus small noise. Extra features (hour, dow, voltage, current, rated_kva) make the
model multi-factor per reviewer feedback (ss.md) - not temperature-only.
"""
from __future__ import annotations

import numpy as np

FEATURES = ["load_w", "temp_c", "hour", "dow", "voltage_v", "current_a", "rated_kva"]
NOMINAL_TEMP_C = 25.0


def tech_loss_w(load_w, temp_c):
    tf = np.maximum(0.2, 1.0 + 0.03 * (temp_c - NOMINAL_TEMP_C))
    return load_w * 0.03 * tf


def make_dataset(n: int = 8000, seed: int = 0):
    rng = np.random.default_rng(seed)
    load = rng.uniform(500, 12000, n)
    temp = rng.uniform(10, 48, n)
    hour = rng.integers(0, 24, n).astype(float)
    dow = rng.integers(0, 7, n).astype(float)
    voltage = rng.normal(230, 4, n)
    current = load / np.maximum(voltage, 1.0)
    rated = rng.choice([250.0, 315.0, 400.0, 630.0], n)
    # mild time-of-day effect on loss (peak hours run hotter cables)
    peak = ((hour >= 12) & (hour <= 17)).astype(float) * 0.05
    y = tech_loss_w(load, temp) * (1.0 + peak + rng.normal(0, 0.05, n))
    X = np.column_stack([load, temp, hour, dow, voltage, current, rated])
    return X, np.maximum(0.0, y)


if __name__ == "__main__":
    X, y = make_dataset()
    print(f"dataset: X={X.shape} features={FEATURES}  y[min/mean/max]="
          f"{y.min():.0f}/{y.mean():.0f}/{y.max():.0f} W")
