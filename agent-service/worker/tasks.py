import asyncio
import logging
from celery import Task
from worker.celery_app import celery_app
from config.settings import settings
from graph.graph import build_graph
from graph.checkpointer import get_checkpointer
from graph.state import ApplicationState
from services.event_publisher import event_publisher

logger = logging.getLogger(__name__)


@celery_app.task(
    name="agent.run_pipeline",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    queue="agent",
)
def run_pipeline(self: Task, application_id: str, initial_data: dict) -> dict:
    """Start a new LangGraph pipeline run for an application."""
    initial_state: ApplicationState = {
        "application_id": application_id,
        "full_name": initial_data.get("full_name", ""),
        "phone": initial_data.get("phone", ""),
        "email": initial_data.get("email", ""),
        "pan_number": initial_data.get("pan_number", ""),
        "loan_amount": float(initial_data.get("loan_amount", 0)),
        "loan_purpose": initial_data.get("loan_purpose", ""),
        "tenure_months": int(initial_data.get("tenure_months", 12)),
        "created_at": initial_data.get("created_at", ""),
        "current_stage": "lead_capture",
        "stage_results": {},
        "pipeline_errors": [],
        "messages": [],
        "disbursement_attempts": 0,
    }

    config = {"configurable": {"thread_id": application_id}}

    try:
        checkpointer = get_checkpointer()
        graph = build_graph(checkpointer=checkpointer)
        result = asyncio.run(graph.ainvoke(initial_state, config=config))
        event_publisher.publish(
            stream="loan:events",
            event_type="node.completed",
            payload={
                "application_id": application_id,
                "stage": result.get("current_stage"),
                "lead_score": result.get("lead_score"),
                "stage_results": result.get("stage_results", {}),
            },
        )
        logger.info("Pipeline completed for %s at stage %s", application_id, result.get("current_stage"))
        return {"application_id": application_id, "stage": result.get("current_stage")}
    except Exception as exc:
        logger.error("Pipeline error for %s: %s", application_id, exc)
        raise self.retry(exc=exc)


@celery_app.task(
    name="agent.resume_pipeline",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    queue="agent",
)
def resume_pipeline(self: Task, application_id: str, hitl_decision: dict) -> dict:
    """Resume a pipeline that was interrupted at the HITL node."""
    # TODO: implement in a later step
    pass


@celery_app.task(
    name="agent.retry_disbursement",
    bind=True,
    max_retries=settings.disbursement_max_retries,
    default_retry_delay=3600,
    queue="agent",
)
def retry_disbursement(self: Task, application_id: str) -> dict:
    """Retry disbursement with exponential back-off."""
    # TODO: implement in a later step
    pass
