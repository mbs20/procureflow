from celery import Celery

from procureflow.config import get_settings

settings = get_settings()

celery_app = Celery(
    "procureflow",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "procureflow.tasks.smoke",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_always_eager=settings.celery_always_eager,
    task_eager_propagates=True,
    broker_connection_retry_on_startup=True,
)
