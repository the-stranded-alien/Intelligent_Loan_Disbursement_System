from celery import Celery
from config.settings import settings

celery_app = Celery(
    "agent-service",
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
    task_default_queue="agent",
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
)
