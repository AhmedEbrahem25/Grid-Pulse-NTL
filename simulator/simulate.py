"""Grid-Pulse NTL simulator — the no-hardware fallback + live data source.

Usage:
  python simulator/simulate.py                 # stream normal telemetry (dashboard looks live)
  python simulator/simulate.py theft           # fire the theft beat once
  python simulator/simulate.py technical        # fire the hot-day / technical-loss beat once

Only stdlib (urllib) so it runs anywhere. Configure via env:
  API=http://localhost:8000  INGEST_TOKEN=dev-token  TRANSFORMER=TX-KFS-0456
"""
from __future__ import annotations

import json
import os
import random
import sys
import time
import urllib.request

API = os.getenv("API", "http://localhost:8000")
TOKEN = os.getenv("INGEST_TOKEN", "dev-token")
TX = os.getenv("TRANSFORMER", "TX-KFS-0456")
REGISTERED_W = 6800.0
seq = int(time.time()) % 100000


def _post(path, body, auth=False):
    data = json.dumps(body).encode()
    req = urllib.request.Request(API + path, data=data, method="POST",
                                 headers={"Content-Type": "application/json"})
    if auth:
        req.add_header("Authorization", f"Bearer {TOKEN}")
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status
    except Exception as e:
        print(f"  POST {path} failed: {e}")
        return None


def ingest(total_w, pf, thd, temp):
    global seq
    seq += 1
    payload = {
        "schema_version": "1.0", "device_id": "GP-EDGE-SIM001", "firmware": "1.0.0",
        "ts": int(time.time()), "seq": seq,
        "site": {"transformer_id": TX, "feeder_id": "F-03", "lat": 31.1107, "lng": 30.9388},
        "measurement": {"window_ms": 1000, "energy_wh_interval": round(total_w / 3600, 3),
                        "phases": [{"phase": "single", "i_rms_a": round(total_w / 230, 1),
                                    "v_rms_v": 230.0, "p_active_w": total_w,
                                    "s_apparent_va": round(total_w / max(pf, .01), 1),
                                    "power_factor": pf, "freq_hz": 49.98, "thd_i_pct": thd}]},
        "env": {"temp_c": temp, "humidity_pct": 50.0},
    }
    return _post("/ingest", payload, auth=True)


def set_registered():
    _post("/meters/reading", {"meter_id": "M-SIM", "transformer_id": TX,
                              "ts": int(time.time()), "energy_wh_interval": REGISTERED_W / 3600,
                              "p_active_w": REGISTERED_W})


if __name__ == "__main__":
    scenario = sys.argv[1] if len(sys.argv) > 1 else None
    set_registered()
    if scenario in ("theft", "technical", "normal"):
        print(f"firing scenario: {scenario}")
        print(_post("/sim/scenario", {"transformer_id": TX, "scenario": scenario}))
        sys.exit(0)

    print(f"streaming normal telemetry for {TX} → {API} (Ctrl-C to stop)")
    while True:
        total = REGISTERED_W + random.uniform(-40, 120)   # small natural variation
        ingest(round(total, 1), pf=round(random.uniform(0.96, 0.99), 3),
               thd=round(random.uniform(3, 6), 1), temp=round(random.uniform(26, 30), 1))
        time.sleep(1)
