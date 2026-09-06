from procureflow.tasks.celery_app import celery_app
from procureflow.tasks.smoke import ping_task

__all__ = ["celery_app", "ping_task"]
