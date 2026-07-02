"""Celery detection task (INLINE_DETECTION=false path).

Pure compute: gets everything via args, computes the verdict, publishes it.
The API stores + forwards it to WebSocket clients.
"""
from __future__ import annotations

from typing import List

from .contract import EdgePayload
from .detection.decision import run_detection
from .queue import celery_app, publish_verdict


@celery_app.task(name="detect")
def detect_task(payload_json: dict, transformer: dict,
                registered_load_w: float, recent_loads: List[float]) -> dict:
    payload = EdgePayload(**payload_json)
    verdict = run_detection(payload, transformer, registered_load_w, recent_loads)
    publish_verdict(verdict)
    return verdict
