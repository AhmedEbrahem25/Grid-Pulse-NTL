"""Train the technical-loss regressor + temporal anomaly model, save artifacts.

Run:  python ml/train.py
Writes ml/artifacts/{tech_loss.pkl, iforest.pkl, meta.json}. docker-compose mounts
./ml/artifacts into the api + worker containers. The backend also has a physics
fallback, so the system works even before this runs.
"""
from __future__ import annotations

import json
import os
import sys

import joblib
import numpy as np
from sklearn.ensemble import IsolationForest, RandomForestRegressor

sys.path.insert(0, os.path.dirname(__file__))
from generate_dataset import FEATURES, make_dataset  # noqa: E402

ART = os.path.join(os.path.dirname(__file__), "artifacts")
os.makedirs(ART, exist_ok=True)


def main():
    X, y = make_dataset(n=8000, seed=0)

    reg = RandomForestRegressor(n_estimators=120, max_depth=14, n_jobs=-1, random_state=0)
    reg.fit(X, y)
    joblib.dump(reg, os.path.join(ART, "tech_loss.pkl"))

    # Temporal anomaly features = [load_w, hour, residual_w, load_w - avg].
    # Normal readings have a *small* residual (measurement noise), not exactly 0 --
    # otherwise the model flags every nonzero residual. Seed realistic jitter so it
    # tolerates small residuals and only large unexplained draws read as outliers.
    rng = np.random.default_rng(0)
    resid_noise = rng.normal(0.0, 90.0, len(X))       # +/- ~90 W normal imbalance
    delta_noise = rng.normal(0.0, 120.0, len(X))      # +/- ~120 W load wobble vs recent avg
    Xa = np.column_stack([X[:, 0], X[:, 2], resid_noise, delta_noise])
    iso = IsolationForest(n_estimators=150, contamination=0.02, random_state=0)
    iso.fit(Xa)
    joblib.dump(iso, os.path.join(ART, "iforest.pkl"))

    json.dump({"features": FEATURES, "n": int(len(X)),
               "importances": dict(zip(FEATURES, [round(float(i), 3) for i in reg.feature_importances_]))},
              open(os.path.join(ART, "meta.json"), "w"), indent=2)

    # sanity: same load/time, hot vs nominal -> hot should predict higher loss
    base = [6000, 25, 14, 2, 230, 26, 400]
    hot = [6000, 45, 14, 2, 230, 26, 400]
    print("feature importances:", dict(zip(FEATURES, np.round(reg.feature_importances_, 3))))
    print(f"expected loss  nominal(25C)={reg.predict([base])[0]:.0f} W   hot(45C)={reg.predict([hot])[0]:.0f} W")
    print(f"artifacts written to {ART}")


if __name__ == "__main__":
    main()
