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
    """Start a new LangGraph pipeline run for an application.

    The graph has interrupt_before=["sanction_processing"], so ainvoke() always
    pauses after document_collection. For loans > HITL_THRESHOLD we wait for RM
    review; for smaller loans we immediately resume.
    """
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

        "date_of_birth":   initial_data.get("date_of_birth"),    # ADD
        "employment_type": initial_data.get("employment_type"),  # ADD
        "monthly_income":  float(initial_data.get("monthly_income") or 0) or None,

        "lead_source":              initial_data.get("lead_source", "web"),
        "branch_code":              initial_data.get("branch_code"),
        "branch_name":              initial_data.get("branch_name"),
        "staff_id":                 initial_data.get("staff_id"),
        "staff_name":               initial_data.get("staff_name"),
        "kyc_physically_seen":      initial_data.get("kyc_physically_seen", False),
        "customer_consent_signed":  initial_data.get("customer_consent_signed", False),

        "scanned_document_path":   initial_data.get("scanned_document_path"),
        "scanned_document_mime":   initial_data.get("scanned_document_mime"),
        "ocr_extraction_status":   None,
        "ocr_extracted_fields":    None,
        "ocr_confidence":          None,
    }

    config = {"configurable": {"thread_id": application_id}}

    async def _run():
        checkpointer = await get_checkpointer()
        graph = build_graph(checkpointer=checkpointer)

        # First ainvoke — runs lead_capture through document_collection,
        # then pauses before sanction_processing (interrupt_before).
        result = await graph.ainvoke(initial_state, config=config)

        loan_amount = result.get("loan_amount", 0)
        if loan_amount > settings.hitl_threshold:
            # Signal backend-api to mark application as pending_review and
            # surface it in the RM dashboard. Pipeline resumes via resume_pipeline
            # once the RM submits a decision.
            event_publisher.publish(
                stream="loan:events",
                event_type="hitl.requested",
                payload={
                    "application_id": application_id,
                    "loan_amount": loan_amount,
                    "stage_results": result.get("stage_results", {}),
                },
            )
            logger.info("Pipeline paused for HITL review: %s (₹%s)",
                        application_id, loan_amount)
            return result

        # Small loan — auto-resume through sanction_processing → disbursement.
        result = await graph.ainvoke(None, config=config)
        return result

    try:
        result = asyncio.run(_run())

        # Only publish pipeline.completed when the pipeline fully finished
        # (i.e. not waiting for HITL). For HITL cases the hitl.requested event
        # was already published above; pipeline.completed fires from resume_pipeline.
        if not (result.get("loan_amount", 0) > settings.hitl_threshold and
                result.get("hitl_decision") is None):
            event_publisher.publish(
                stream="loan:events",
                event_type="pipeline.completed",
                payload={
                    "application_id": application_id,
                    "stage": result.get("current_stage"),
                    "lead_score": result.get("lead_score"),
                    "stage_results": result.get("stage_results", {}),
                },
            )

        logger.info("Pipeline task done for %s at stage %s",
                    application_id, result.get("current_stage"))
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
    """Resume a pipeline that was interrupted at the HITL node.

    Injects the RM decision into the checkpoint state, then resumes the graph
    from sanction_processing through to disbursement.
    """
    config = {"configurable": {"thread_id": application_id}}

    async def _resume():
        checkpointer = await get_checkpointer()
        graph = build_graph(checkpointer=checkpointer)

        # Inject the RM decision into the persisted checkpoint state so that
        # sanction_processing can see it when the graph resumes.
        await graph.aupdate_state(
            config,
            values={
                "hitl_decision": hitl_decision.get("decision"),
                "hitl_notes": hitl_decision.get("notes", ""),
                "rm_id": hitl_decision.get("rm_id", ""),
            },
        )

        # Resume — graph continues from sanction_processing.
        result = await graph.ainvoke(None, config=config)
        return result

    try:
        result = asyncio.run(_resume())
        event_publisher.publish(
            stream="loan:events",
            event_type="pipeline.completed",
            payload={
                "application_id": application_id,
                "stage": result.get("current_stage"),
                "lead_score": result.get("lead_score"),
                "stage_results": result.get("stage_results", {}),
            },
        )
        logger.info("Pipeline resumed and completed for %s", application_id)
        return {"application_id": application_id, "stage": result.get("current_stage")}
    except Exception as exc:
        logger.error("Resume pipeline error for %s: %s", application_id, exc)
        raise self.retry(exc=exc)


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
