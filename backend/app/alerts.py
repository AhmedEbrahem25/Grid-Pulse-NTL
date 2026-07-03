"""Theft alerts (A4) — push a NTL_THEFT_SUSPECTED verdict to a webhook / Telegram.

Everything is optional and best-effort: if nothing is configured (or the POST
fails) it silently no-ops, so the demo is never blocked by the network.
"""
from __future__ import annotations

import asyncio

from .config import settings


def _summary(v: dict) -> str:
    kw = v.get("theft_estimate_w", 0) / 1000.0
    return (f"⚡ THEFT SUSPECTED — {v.get('transformer_id')} · "
            f"{v.get('theft_probability')}% · ~{kw:.2f} kW unaccounted · "
            f"severity {v.get('severity')}")


async def _post(url: str, json_body: dict) -> None:
    try:
        import httpx
        async with httpx.AsyncClient(timeout=5) as c:
            await c.post(url, json=json_body)
    except Exception:
        pass


async def _fire(v: dict) -> None:
    text = _summary(v)
    if settings.alert_webhook_url:
        await _post(settings.alert_webhook_url, {"text": text, "verdict": v})
    if settings.telegram_bot_token and settings.telegram_chat_id:
        await _post(
            f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage",
            {"chat_id": settings.telegram_chat_id, "text": text})


def notify_theft(v: dict) -> None:
    """Fire-and-forget; returns immediately. Only acts on a theft verdict with a sink configured."""
    if v.get("label") != "NTL_THEFT_SUSPECTED":
        return
    if not (settings.alert_webhook_url or (settings.telegram_bot_token and settings.telegram_chat_id)):
        return
    try:
        asyncio.get_running_loop().create_task(_fire(v))
    except RuntimeError:
        pass  # no running loop (e.g. Celery worker) — skip
