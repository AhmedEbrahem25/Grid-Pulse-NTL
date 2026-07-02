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


settings = Settings()
