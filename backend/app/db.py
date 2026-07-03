"""Durable persistence (A1) — SQLModel over SQLite (Postgres-ready via DATABASE_URL).

Verdicts + a per-transformer loss time-series survive restarts, and power the
GET /transformers/{id}/history endpoint. Every call is best-effort: if SQLModel
isn't importable or the store can't be opened, the whole module no-ops and the
backend runs exactly as before (pure in-memory). The demo never depends on it.
"""
from __future__ import annotations

import json
import os
from typing import List, Optional

_engine = None
_ok = False

try:
    from sqlmodel import Field, Session, SQLModel, create_engine, select

    class VerdictRow(SQLModel, table=True):
        id: Optional[int] = Field(default=None, primary_key=True)
        vid: str = Field(index=True)
        transformer_id: str = Field(index=True)
        created_at: int = Field(index=True)
        label: str = ""
        theft_probability: int = 0
        measured_loss_w: float = 0.0
        severity: str = ""
        status: str = "open"
        payload_json: str = ""

    class ReadingRow(SQLModel, table=True):
        id: Optional[int] = Field(default=None, primary_key=True)
        transformer_id: str = Field(index=True)
        ts: int = Field(index=True)
        load_w: float = 0.0
        power_factor: float = 0.0
        thd_i_pct: float = 0.0

    _HAVE = True
except Exception:  # pragma: no cover - sqlmodel absent
    _HAVE = False


def init() -> bool:
    global _engine, _ok
    if _ok or not _HAVE:
        return _ok
    try:
        from .config import settings
        url = settings.database_url
        if url.startswith("sqlite"):
            path = url.replace("sqlite:///", "", 1)          # sqlite:////data/x.db -> /data/x.db
            d = os.path.dirname(path)
            if d and not os.path.isdir(d):
                try:
                    os.makedirs(d, exist_ok=True)
                except Exception:
                    url = "sqlite:///./gridpulse.db"          # fall back to cwd
        connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
        _engine = create_engine(url, connect_args=connect_args)
        SQLModel.metadata.create_all(_engine)
        _ok = True
    except Exception as e:
        print(f"[db] persistence disabled: {e}")
        _ok = False
    return _ok


def save_verdict(v: dict) -> None:
    if not _ok:
        return
    try:
        with Session(_engine) as s:
            s.add(VerdictRow(
                vid=v.get("id", ""), transformer_id=v.get("transformer_id", ""),
                created_at=int(v.get("created_at", 0)), label=v.get("label", ""),
                theft_probability=int(v.get("theft_probability", 0)),
                measured_loss_w=float(v.get("measured_loss_w", 0.0)),
                severity=v.get("severity", ""), status=v.get("status", "open"),
                payload_json=json.dumps(v)))
            s.commit()
    except Exception:
        pass


def set_status(vid: str, status: str) -> None:
    if not _ok:
        return
    try:
        with Session(_engine) as s:
            for row in s.exec(select(VerdictRow).where(VerdictRow.vid == vid)):
                row.status = status
                data = json.loads(row.payload_json or "{}"); data["status"] = status
                row.payload_json = json.dumps(data); s.add(row)
            s.commit()
    except Exception:
        pass


def load_recent_verdicts(limit: int = 300) -> List[dict]:
    if not _ok:
        return []
    try:
        with Session(_engine) as s:
            rows = s.exec(select(VerdictRow).order_by(VerdictRow.created_at.desc()).limit(limit)).all()
            return [json.loads(r.payload_json) for r in rows if r.payload_json]
    except Exception:
        return []


def save_reading(transformer_id: str, r: dict) -> None:
    if not _ok:
        return
    try:
        with Session(_engine) as s:
            s.add(ReadingRow(transformer_id=transformer_id, ts=int(r.get("ts", 0)),
                             load_w=float(r.get("p_active_w", 0.0)),
                             power_factor=float(r.get("power_factor", 0.0)),
                             thd_i_pct=float(r.get("thd_i_pct", 0.0))))
            s.commit()
    except Exception:
        pass


def clear() -> None:
    """Truncate persisted verdicts + readings (Reset Demo). No-op if unavailable."""
    if not _ok:
        return
    try:
        with Session(_engine) as s:
            for row in s.exec(select(VerdictRow)).all():
                s.delete(row)
            for row in s.exec(select(ReadingRow)).all():
                s.delete(row)
            s.commit()
    except Exception:
        pass


def history(transformer_id: str, hours: float = 24.0) -> dict:
    """Loss/verdict + load series for GET /transformers/{id}/history."""
    if not _ok:
        return {"verdicts": [], "readings": []}
    import time
    since = int(time.time() - hours * 3600)
    try:
        with Session(_engine) as s:
            vr = s.exec(select(VerdictRow).where(VerdictRow.transformer_id == transformer_id)
                        .where(VerdictRow.created_at >= since)
                        .order_by(VerdictRow.created_at)).all()
            rr = s.exec(select(ReadingRow).where(ReadingRow.transformer_id == transformer_id)
                        .where(ReadingRow.ts >= since)
                        .order_by(ReadingRow.ts).limit(500)).all()
            return {
                "verdicts": [{"ts": r.created_at, "label": r.label,
                              "theft_probability": r.theft_probability,
                              "measured_loss_w": r.measured_loss_w} for r in vr],
                "readings": [{"ts": r.ts, "load_w": r.load_w,
                              "thd_i_pct": r.thd_i_pct} for r in rr],
            }
    except Exception:
        return {"verdicts": [], "readings": []}
