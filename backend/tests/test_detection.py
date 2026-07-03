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


H_LEGIT = [{"h": 5, "mag_pct": 14}, {"h": 7, "mag_pct": 8}, {"h": 11, "mag_pct": 4}, {"h": 13, "mag_pct": 3}]
H_ILLEGAL = [{"h": 2, "mag_pct": 4}, {"h": 3, "mag_pct": 18}, {"h": 4, "mag_pct": 4}, {"h": 5, "mag_pct": 20},
             {"h": 7, "mag_pct": 13}, {"h": 9, "mag_pct": 8}, {"h": 11, "mag_pct": 6}, {"h": 13, "mag_pct": 5}]


def payload(total, pf, thd, temp, harmonics=None):
    phase = {"phase": "single", "i_rms_a": total / 230, "v_rms_v": 230.0,
             "p_active_w": total, "s_apparent_va": total / pf,
             "power_factor": pf, "freq_hz": 49.98, "thd_i_pct": thd}
    if harmonics:
        phase["harmonics"] = harmonics
    return EdgePayload(**{
        "schema_version": "1.0", "device_id": "GP-EDGE-TEST01", "firmware": "1.0.0",
        "ts": int(time.time()), "seq": 1,
        "site": {"transformer_id": "TX-KFS-0456"},
        "measurement": {"window_ms": 1000, "energy_wh_interval": total / 3600, "phases": [phase]},
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


def test_industrial_legit_not_theft():
    # high THD + PF dip but a *registered* factory with a legit harmonic signature
    # -> the 1D-CNN clears it, NO false alarm (the "AI beats the rule" beat).
    v = run_detection(payload(8800, 0.93, 20, 27, H_LEGIT), TX, 8800.0, [])
    assert v["label"] == "NORMAL", v
    assert v["theft_probability"] == 0, v
    assert v["harmonic_class"] == "legit_industrial", v


def test_theft_illegal_signature():
    v = run_detection(payload(10200, 0.66, 22, 27, H_ILLEGAL), TX, REGISTERED, [])
    assert v["label"] == "NTL_THEFT_SUSPECTED", v
    assert v["harmonic_class"] == "illegal_bypass", v
    assert v["theft_probability"] >= 80, v


def test_accounting_layer():
    # brazen theft: the accounting layer supports, and the headline is preserved (~94)
    v = run_detection(payload(10200, 0.66, 22, 27, H_ILLEGAL), TX, REGISTERED, [])
    a = v.get("accounting")
    assert a, "accounting evidence missing"
    for k in ("incoming_kwh", "registered_kwh", "actual_loss_kwh", "expected_technical_kwh",
              "excess_loss_kwh", "contribution_pct", "risk_score", "stance", "applied_contribution"):
        assert k in a, k
    assert a["stance"] == "supporting", a
    assert 90 <= v["theft_probability"] <= 97, v["theft_probability"]      # headline stays ~94
    # normal: accounting does NOT support theft, probability stays 0
    vn = run_detection(payload(6850, 0.98, 4, 27), TX, REGISTERED, [])
    assert vn["theft_probability"] == 0, vn
    assert vn["accounting"]["stance"] != "supporting", vn["accounting"]


def test_contract_rejects_junk():
    import pydantic
    try:
        EdgePayload(**{"schema_version": "1.0", "device_id": "bad id!", "ts": 1, "seq": 0,
                       "site": {"transformer_id": "TX-X"}, "measurement": {"window_ms": 1, "phases": []}})
        assert False, "should have rejected"
    except pydantic.ValidationError:
        pass


if __name__ == "__main__":
    test_normal(); test_technical_not_theft(); test_theft()
    test_industrial_legit_not_theft(); test_theft_illegal_signature()
    test_accounting_layer(); test_contract_rejects_junk()
    print("OK — 4 beats classify correctly; accounting layer folds in (headline preserved); contract rejects junk")
