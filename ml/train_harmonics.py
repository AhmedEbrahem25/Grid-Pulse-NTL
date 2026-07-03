"""Train a tiny 1D-CNN over the current-harmonic spectrum → 3-class signature.

    clean / legit_industrial / illegal_bypass

Writes ml/artifacts/harmonic_cnn.pt (state_dict) + harmonic_meta.json.
Runs CPU-only inside the api container:  python ml/train_harmonics.py

The backend loads this in detection/harmonic_cnn.py and degrades to a rule if
torch or the artifact is missing — so the demo never depends on it.
"""
from __future__ import annotations

import json
import os

import numpy as np

from generate_harmonics import CLASSES, NBINS, make_dataset

ART = os.path.join(os.path.dirname(__file__), "artifacts")
os.makedirs(ART, exist_ok=True)


def main():
    import torch
    import torch.nn as nn

    torch.manual_seed(0)
    X, y = make_dataset(n=9000, seed=1)
    # per-bin standardization (store mean/std for inference)
    mean = X.mean(0); std = X.std(0) + 1e-6
    Xn = (X - mean) / std
    n_val = 1500
    Xtr, ytr = Xn[:-n_val], y[:-n_val]
    Xva, yva = Xn[-n_val:], y[-n_val:]

    def to_t(a, dt): return torch.tensor(a, dtype=dt)
    Xtr_t = to_t(Xtr, torch.float32).unsqueeze(1)   # (N,1,NBINS)
    ytr_t = to_t(ytr, torch.long)
    Xva_t = to_t(Xva, torch.float32).unsqueeze(1)
    yva_t = to_t(yva, torch.long)

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

    model = HarmonicCNN()
    opt = torch.optim.Adam(model.parameters(), lr=2e-3)
    lossf = nn.CrossEntropyLoss()
    for epoch in range(60):
        model.train(); opt.zero_grad()
        out = model(Xtr_t); loss = lossf(out, ytr_t)
        loss.backward(); opt.step()
    model.eval()
    with torch.no_grad():
        pred = model(Xva_t).argmax(1)
        acc = (pred == yva_t).float().mean().item()

    torch.save(model.state_dict(), os.path.join(ART, "harmonic_cnn.pt"))
    json.dump({"classes": CLASSES, "nbins": NBINS,
               "mean": mean.tolist(), "std": std.tolist(),
               "val_accuracy": round(acc, 4)},
              open(os.path.join(ART, "harmonic_meta.json"), "w"), indent=2)
    print(f"harmonic 1D-CNN trained — val accuracy {acc:.3f} on {n_val} held-out signatures")
    print(f"artifacts: {ART}/harmonic_cnn.pt, harmonic_meta.json")


if __name__ == "__main__":
    main()
