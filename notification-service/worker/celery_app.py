from celery import Celery
from config.settings import settings

celery_app = Celery(
    "notification-service",
    broker=settings.redis_celery_url,
    backend=settings.redis_celery_url,
    include=["worker.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_default_queue="notifications",
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)
