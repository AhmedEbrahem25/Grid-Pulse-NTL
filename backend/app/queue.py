"""Celery app + a helper to publish verdicts back to the API (Celery mode).

Only used when INLINE_DETECTION=false. The worker is a *stateless compute* node:
it receives everything it needs in the task args, computes the verdict, and
publishes it on a Redis channel. The API owns the store and forwards to WS.
"""
from __future__ import annotations

import json

from celery import Celery

from .config import settings

celery_app = Celery(
    "gridpulse",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.tasks"],
)
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_ignore_result=True,
)


def publish_verdict(verdict: dict) -> None:
    try:
        import redis
        redis.from_url(settings.redis_url).publish(settings.verdict_channel, json.dumps(verdict))
    except Exception:
        pass
