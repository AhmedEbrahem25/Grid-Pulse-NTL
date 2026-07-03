"""Runtime settings, read from environment (no extra deps)."""
import os


class Settings:
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    ingest_token: str = os.getenv("INGEST_TOKEN", "dev-token")
    # True  -> /ingest runs detection inline (no Celery needed; simplest, demo-safe).
    # False -> /ingest enqueues to Celery; the worker runs detection + publishes verdicts.
    inline_detection: bool = os.getenv("INLINE_DETECTION", "true").lower() == "true"

    artifacts_dir: str = os.getenv("ARTIFACTS_DIR", "artifacts")
    # Detection thresholds (see plan/02-detection-and-ai.md).
    residual_alert_w: float = float(os.getenv("RESIDUAL_ALERT_W", "400"))
    healthy_pf: float = float(os.getenv("HEALTHY_PF", "0.92"))
    thd_alert_pct: float = float(os.getenv("THD_ALERT_PCT", "10"))

    verdict_channel: str = "verdicts"  # Redis pub/sub channel worker -> api (Celery mode)

    # Persistence (A1). SQLite by default; point at Postgres in production.
    database_url: str = os.getenv("DATABASE_URL", "sqlite:////data/gridpulse.db")

    # Always-on live stream (A3): gentle background telemetry so the console
    # looks alive with no clicking. Injected demo beats still take priority.
    auto_stream: bool = os.getenv("AUTO_STREAM", "true").lower() == "true"
    auto_stream_interval_s: float = float(os.getenv("AUTO_STREAM_INTERVAL_S", "4"))

    # Transformer Energy Accounting Layer (independent evidence module).
    accounting_horizon_h: float = float(os.getenv("ACCOUNTING_HORIZON_H", "1.0"))
    accounting_k: float = float(os.getenv("ACCOUNTING_K", "1.4"))          # excess% -> contribution scale
    accounting_neutral_contrib: float = float(os.getenv("ACCOUNTING_NEUTRAL", "18"))  # damping baseline

    # Theft alerts (A4): all optional — no-op if unset, never blocks the demo.
    alert_webhook_url: str = os.getenv("ALERT_WEBHOOK_URL", "")
    telegram_bot_token: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    telegram_chat_id: str = os.getenv("TELEGRAM_CHAT_ID", "")


settings = Settings()
