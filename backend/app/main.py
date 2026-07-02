"""Grid-Pulse NTL - FastAPI backend.

Endpoints (see plan/01-architecture.md and contracts/README.md):
  POST /ingest              - Edge telemetry (Strict Contract; 422 on violation)
  POST /meters/reading      - registered (metered) consumption for the balance
  GET  /transformers        - list + latest verdict (map)
  GET  /transformers/{id}   - detail + recent readings + verdicts
  GET  /verdicts            - filterable verdict feed
  POST /verdicts/{id}/status- update a verdict's status
  POST /sim/scenario        - run a demo beat (normal|technical|theft) end-to-end
  WS   /ws/stream           - live edge_reading / verdict / transformer_status
  GET  /healthz             - health
  GET  /                    - dashboard
"""
from __future__ import annotations

import asyncio
import json
import os
import time
from typing import Optional

from fastapi import Depends, FastAPI, Header, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse

from . import store
from .config import settings
from .contract import EdgePayload, MeterReading
from .detection.decision import run_detection
from .ws import ws_manager

app = FastAPI(title="Grid-Pulse NTL", version="1.0.0")


# ---------- auth ----------
def require_ingest_token(authorization: Optional[str] = Header(default=None)) -> None:
    expected = f"Bearer {settings.ingest_token}"
    if authorization != expected:
        raise HTTPException(status_code=401, detail="invalid or missing ingest token")


# ---------- startup ----------
@app.on_event("startup")
async def _startup() -> None:
    store.seed()
    if not settings.inline_detection:
        asyncio.create_task(_verdict_subscriber())


async def _verdict_subscriber() -> None:
    """Celery mode: forward worker verdicts (Redis pub/sub) to store + WS."""
    try:
        import redis.asyncio as aioredis
        r = aioredis.from_url(settings.redis_url)
        pubsub = r.pubsub()
        await pubsub.subscribe(settings.verdict_channel)
        async for msg in pubsub.listen():
            if msg.get("type") != "message":
                continue
            verdict = json.loads(msg["data"])
            await _emit_verdict(verdict)
    except Exception as e:  # pragma: no cover
        print(f"[verdict_subscriber] disabled: {e}")


# ---------- core processing ----------
async def _emit_verdict(verdict: dict) -> dict:
    verdict = store.add_verdict(verdict)
    await ws_manager.broadcast({"type": "verdict", "payload": verdict})
    await ws_manager.broadcast({"type": "transformer_status",
                                "payload": {"transformer_id": verdict["transformer_id"],
                                            "label": verdict["label"], "severity": verdict["severity"]}})
    return verdict


async def process_reading(payload: EdgePayload) -> Optional[dict]:
    tid = payload.site.transformer_id
    reading = {
        "ts": payload.ts,
        "p_active_w": payload.total_active_w(),
        "power_factor": payload.worst_power_factor(),
        "thd_i_pct": payload.max_thd(),
        "phase": payload.primary_phase(),
        "temp_c": payload.env.temp_c if payload.env else None,
    }
    store.add_reading(tid, reading)
    await ws_manager.broadcast({"type": "edge_reading", "payload": {"transformer_id": tid, **reading}})

    transformer = store.transformers.get(tid, {"id": tid, "name": tid, "rated_kva": 400})
    reg = store.get_registered_load(tid)
    recent = store.recent_loads(tid)

    if settings.inline_detection:
        verdict = run_detection(payload, transformer, reg, recent)
        return await _emit_verdict(verdict)

    from .tasks import detect_task
    detect_task.delay(payload.model_dump(), transformer, reg, recent)  # worker publishes back
    return None


# ---------- endpoints ----------
@app.get("/healthz")
async def healthz():
    return {"status": "ok", "inline_detection": settings.inline_detection}


@app.post("/ingest")
async def ingest(payload: EdgePayload, _=Depends(require_ingest_token)):
    verdict = await process_reading(payload)
    return {"accepted": True, "reading_id": f"{payload.device_id}:{payload.seq}",
            "verdict": verdict}


@app.post("/meters/reading")
async def meters_reading(reading: MeterReading):
    if not reading.transformer_id:
        raise HTTPException(status_code=422, detail="transformer_id required")
    # Demo: treat the posted active power as the transformer's current registered total.
    store.set_registered_load(reading.transformer_id, reading.p_active_w)
    return {"ok": True}


@app.get("/transformers")
async def transformers():
    return store.list_transformers()


@app.get("/transformers/{tid}")
async def transformer_detail(tid: str):
    t = store.transformers.get(tid)
    if not t:
        raise HTTPException(status_code=404, detail="unknown transformer")
    return {
        **t,
        "registered_load_w": store.get_registered_load(tid),
        "readings": list(store.readings[tid])[-60:],
        "verdicts": [v for v in store.verdicts if v["transformer_id"] == tid][:20],
    }


@app.get("/verdicts")
async def verdicts(label: Optional[str] = None, severity: Optional[str] = None,
                   status: Optional[str] = None):
    out = store.verdicts
    if label:
        out = [v for v in out if v["label"] == label]
    if severity:
        out = [v for v in out if v["severity"] == severity]
    if status:
        out = [v for v in out if v.get("status") == status]
    return out[:100]


@app.post("/verdicts/{vid}/status")
async def set_status(vid: str, body: dict):
    status = body.get("status")
    if status not in {"open", "dispatched", "confirmed", "dismissed"}:
        raise HTTPException(status_code=422, detail="bad status")
    v = store.set_verdict_status(vid, status)
    if not v:
        raise HTTPException(status_code=404, detail="unknown verdict")
    await ws_manager.broadcast({"type": "verdict", "payload": v})
    return v


# ---------- demo scenarios (run a beat end-to-end without hardware) ----------
BASE_REGISTERED_W = 6800.0
_seq = {"n": 5000}


def _scenario_payload(tid: str, scenario: str) -> EdgePayload:
    _seq["n"] += 1
    presets = {
        # scenario: (total_w, power_factor, thd, temp_c)
        "normal":    (6850.0, 0.98, 4.0, 27.0),
        "technical": (7000.0, 0.97, 5.0, 45.0),   # hot day: baseline rises, no alarm
        "theft":     (10200.0, 0.66, 22.0, 27.0),  # brazen unregistered ~3.4 kW hook: PF collapses, THD spikes
    }
    total, pf, thd, temp = presets.get(scenario, presets["normal"])
    return EdgePayload(
        schema_version="1.0", device_id="GP-EDGE-SIM001", firmware="1.0.0",
        ts=int(time.time()), seq=_seq["n"],
        site={"transformer_id": tid, "feeder_id": "F-03", "lat": 31.1107, "lng": 30.9388},
        measurement={"window_ms": 1000, "energy_wh_interval": round(total / 3600, 3),
                     "phases": [{"phase": "single", "i_rms_a": round(total / 230, 1),
                                 "v_rms_v": 230.0, "p_active_w": total,
                                 "s_apparent_va": round(total / max(pf, 0.01), 1),
                                 "power_factor": pf, "freq_hz": 49.98, "thd_i_pct": thd}]},
        env={"temp_c": temp, "humidity_pct": 50.0},
    )


@app.post("/sim/scenario")
async def sim_scenario(body: dict):
    tid = body.get("transformer_id", "TX-KFS-0456")
    scenario = body.get("scenario", "normal")
    if scenario not in {"normal", "technical", "theft"}:
        raise HTTPException(status_code=422, detail="scenario must be normal|technical|theft")
    store.set_registered_load(tid, BASE_REGISTERED_W)
    verdict = await process_reading(_scenario_payload(tid, scenario))
    return {"ok": True, "verdict": verdict}


# ---------- websocket ----------
@app.websocket("/ws/stream")
async def ws_stream(ws: WebSocket):
    await ws_manager.connect(ws)
    try:
        while True:
            await ws.receive_text()  # keepalive / ignore client messages
    except WebSocketDisconnect:
        ws_manager.disconnect(ws)


# ---------- dashboard ----------
def _dashboard_file() -> Optional[str]:
    for p in ("/app/dashboard/index.html",
              os.path.join(os.path.dirname(__file__), "..", "..", "dashboard", "index.html")):
        if os.path.exists(p):
            return os.path.abspath(p)
    return None


@app.get("/")
async def root():
    f = _dashboard_file()
    if f:
        return FileResponse(f)
    return JSONResponse({"service": "grid-pulse-ntl", "docs": "/docs",
                         "hint": "dashboard/index.html not found; API is up"})
