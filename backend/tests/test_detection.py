"""Verifies the three demo beats classify correctly + the contract rejects junk.
Run:  python backend/tests/test_detection.py    (or: pytest backend/tests)
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # backend/

from app.contract import EdgePayload  # noqa: E402
from app.detection.decision import run_detection  # noqa: E402

TX = {"id": "TX-KFS-0456", "rated_kva": 400}
REGISTERED = 6800.0


def payload(total, pf, thd, temp):
    return EdgePayload(**{
        "schema_version": "1.0", "device_id": "GP-EDGE-TEST01", "firmware": "1.0.0",
        "ts": int(time.time()), "seq": 1,
        "site": {"transformer_id": "TX-KFS-0456"},
        "measurement": {"window_ms": 1000, "energy_wh_interval": total / 3600,
                        "phases": [{"phase": "single", "i_rms_a": total / 230, "v_rms_v": 230.0,
                                    "p_active_w": total, "s_apparent_va": total / pf,
                                    "power_factor": pf, "freq_hz": 49.98, "thd_i_pct": thd}]},
        "env": {"temp_c": temp},
    })


def test_normal():
    v = run_detection(payload(6850, 0.98, 4, 27), TX, REGISTERED, [])
    assert v["label"] == "NORMAL", v


def test_technical_not_theft():
    v = run_detection(payload(7000, 0.97, 5, 45), TX, REGISTERED, [])
    assert v["label"] == "TECHNICAL_LOSS", v   # hot day explained, NOT theft


def test_theft():
    v = run_detection(payload(8990, 0.71, 18, 27), TX, REGISTERED, [])
    assert v["label"] == "NTL_THEFT_SUSPECTED", v
    assert v["theft_probability"] > 0
    assert any(r["label"] == "Energy imbalance" and r["met"] for r in v["reasons"])
    assert any(r["label"] == "Power factor dropped" and r["met"] for r in v["reasons"])


def test_contract_rejects_junk():
    import pydantic
    try:
        EdgePayload(**{"schema_version": "1.0", "device_id": "bad id!", "ts": 1, "seq": 0,
                       "site": {"transformer_id": "TX-X"}, "measurement": {"window_ms": 1, "phases": []}})
        assert False, "should have rejected"
    except pydantic.ValidationError:
        pass


if __name__ == "__main__":
    test_normal(); test_technical_not_theft(); test_theft(); test_contract_rejects_junk()
    print("OK — normal / technical / theft classify correctly; contract rejects junk")
