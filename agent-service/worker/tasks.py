from celery import Task
from worker.celery_app import celery_app
from config.settings import settings


@celery_app.task(
    name="agent.run_pipeline",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    queue="agent",
)
def run_pipeline(self: Task, application_id: str, initial_data: dict) -> dict:
    """Start a new LangGraph pipeline run for an application."""
    # TODO: Build initial ApplicationState, invoke graph.compile().ainvoke()
    pass


@celery_app.task(
    name="agent.resume_pipeline",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    queue="agent",
)
def resume_pipeline(self: Task, application_id: str, hitl_decision: dict) -> dict:
    """Resume a pipeline that was interrupted at the HITL node."""
    # TODO: Load checkpoint, inject RM decision into state, resume graph
    pass


@celery_app.task(
    name="agent.retry_disbursement",
    bind=True,
    max_retries=settings.disbursement_max_retries,
    default_retry_delay=3600,  # 1 hour; overridden per attempt in the task body
    queue="agent",
)
def retry_disbursement(self: Task, application_id: str) -> dict:
    """Retry disbursement with exponential back-off: immediate → 1h → 4h → 24h."""
    # TODO: Re-run disbursement agent node; implement back-off countdown per attempt
    pass
