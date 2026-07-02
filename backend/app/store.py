"""In-memory store (hackathon-grade). Swap for Postgres post-event.

Holds transformers, the latest *registered* load per transformer (for the
energy balance), recent edge readings, and verdicts.
"""
from __future__ import annotations

import itertools
import threading
import time
import uuid
from collections import defaultdict, deque
from typing import Deque, Dict, List, Optional

_lock = threading.Lock()

transformers: Dict[str, dict] = {}
# latest registered (legal, metered) consumption per transformer, in watts
registered_load_w: Dict[str, float] = defaultdict(float)
readings: Dict[str, Deque[dict]] = defaultdict(lambda: deque(maxlen=300))
verdicts: List[dict] = []
_verdict_seq = itertools.count(1)


def seed() -> None:
    """A small city of transformers around Kafr El-Sheikh for the map/demo."""
    if transformers:
        return
    demo = [
        ("TX-KFS-0456", "Downtown Feeder 3", 31.1107, 30.9388, 400),
        ("TX-KFS-0457", "Industrial Zone A", 31.1180, 30.9500, 630),
        ("TX-KFS-0458", "Riverside", 31.1050, 30.9300, 250),
        ("TX-KFS-0459", "North Housing", 31.1240, 30.9410, 400),
        ("TX-KFS-0460", "Market Square", 31.1090, 30.9450, 315),
    ]
    for tid, name, lat, lng, kva in demo:
        transformers[tid] = {
            "id": tid, "name": name, "feeder_id": tid.split("-")[-1],
            "lat": lat, "lng": lng, "rated_kva": kva,
        }
        registered_load_w[tid] = 0.0


def set_registered_load(transformer_id: str, watts: float) -> None:
    with _lock:
        registered_load_w[transformer_id] = max(0.0, watts)


def get_registered_load(transformer_id: str) -> float:
    return registered_load_w.get(transformer_id, 0.0)


def add_reading(transformer_id: str, reading: dict) -> None:
    with _lock:
        readings[transformer_id].append(reading)


def recent_loads(transformer_id: str, n: int = 60) -> List[float]:
    return [r["p_active_w"] for r in list(readings[transformer_id])[-n:]]


def add_verdict(v: dict) -> dict:
    with _lock:
        v = {"id": f"V-{next(_verdict_seq):05d}", "created_at": int(time.time()), **v}
        verdicts.insert(0, v)
        del verdicts[500:]  # cap
    return v


def set_verdict_status(verdict_id: str, status: str) -> Optional[dict]:
    with _lock:
        for v in verdicts:
            if v["id"] == verdict_id:
                v["status"] = status
                return v
    return None


def latest_verdict(transformer_id: str) -> Optional[dict]:
    for v in verdicts:
        if v["transformer_id"] == transformer_id:
            return v
    return None


def list_transformers() -> List[dict]:
    return [{**t, "latest_verdict": latest_verdict(t["id"])} for t in transformers.values()]
