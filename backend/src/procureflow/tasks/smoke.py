import time

from procureflow.tasks.celery_app import celery_app


@celery_app.task(name="procureflow.tasks.smoke.ping")
def ping_task(message: str = "pong") -> dict:
    """Smoke test task to verify Celery worker connectivity."""
    return {
        "status": "success",
        "message": message,
        "timestamp": time.time(),
    }
