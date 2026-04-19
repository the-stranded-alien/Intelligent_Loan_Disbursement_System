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

    The graph has interrupt_before=["art_negotiation"], so ainvoke() always
    pauses after credit_assessment. We detect whether the graph actually
    interrupted (pipeline paused awaiting HITL / auto-resume) or ended early
    (rejected at Node 1–4) by inspecting state_snapshot.next after ainvoke.
    """
    initial_state: ApplicationState = {
        "application_id": application_id,
        "full_name": initial_data.get("full_name", ""),
        "phone": initial_data.get("phone", ""),
        "email": initial_data.get("email", ""),
        "pan_number": initial_data.get("pan_number", ""),
        "date_of_birth": initial_data.get("date_of_birth", ""),
        "city": initial_data.get("city", ""),
        "state": initial_data.get("state", ""),
        "residential_status": initial_data.get("residential_status", ""),
        "years_at_current_address": int(initial_data.get("years_at_current_address", 0)),
        "employment_type": initial_data.get("employment_type", "salaried"),
        "employer_name": initial_data.get("employer_name", ""),
        "years_in_current_job": int(initial_data.get("years_in_current_job", 0)),
        "monthly_income": float(initial_data.get("monthly_income", 0)),
        "existing_emi_amount": float(initial_data.get("existing_emi_amount", 0)),
        "bank_account_number": initial_data.get("bank_account_number", ""),
        "ifsc_code": initial_data.get("ifsc_code", ""),
        "loan_amount": float(initial_data.get("loan_amount", 0)),
        "loan_purpose": initial_data.get("loan_purpose", ""),
        "tenure_months": int(initial_data.get("tenure_months", 12)),
        "created_at": initial_data.get("created_at", ""),
        "current_stage": "lead_capture",
        "stage_results": {},
        "pipeline_errors": [],
        "messages": [],
    }

    config = {"configurable": {"thread_id": application_id}}

    async def _run():
        checkpointer = await get_checkpointer()
        graph = build_graph(checkpointer=checkpointer)

        # First ainvoke — runs Nodes 1–4 then pauses before art_negotiation
        # (due to interrupt_before). If pipeline rejects early (Node 1/2/3/4),
        # ainvoke also returns but the graph has no next nodes.
        result = await graph.ainvoke(initial_state, config=config)

        # Reliable interrupt detection: if graph.next is non-empty the
        # pipeline was paused (interrupted); if empty it reached END.
        snapshot = await graph.aget_state(config)
        is_interrupted = bool(snapshot.next)

        loan_amount = result.get("loan_amount", 0)

        if is_interrupted:
            # Pipeline paused before art_negotiation — large loan → wait for RM.
            if loan_amount > settings.hitl_threshold:
                event_publisher.publish(
                    stream="loan:events",
                    event_type="hitl.requested",
                    payload={
                        "application_id": application_id,
                        "loan_amount": loan_amount,
                        "stage_results": result.get("stage_results", {}),
                    },
                )
                logger.info("Pipeline paused for HITL: %s (₹%s)", application_id, loan_amount)
                return result

            # Small loan — auto-resume through art_negotiation → enach → esign.
            result = await graph.ainvoke(None, config=config)
            _publish_completed(application_id, result, "completed")
        else:
            # Pipeline ended early (rejected at Node 1/2/3/4).
            _publish_completed(application_id, result, "rejected")

        return result

    try:
        result = asyncio.run(_run())
        logger.info("Pipeline task done for %s at stage %s", application_id, result.get("current_stage"))
        return {"application_id": application_id, "stage": result.get("current_stage")}
    except Exception as exc:
        logger.error("Pipeline error for %s: %s", application_id, exc)
        raise self.retry(exc=exc)


def _publish_completed(application_id: str, result: dict, final_status: str):
    event_publisher.publish(
        stream="loan:events",
        event_type="pipeline.completed",
        payload={
            "application_id": application_id,
            "stage": result.get("current_stage"),
            "final_status": final_status,
            "stage_results": result.get("stage_results", {}),
        },
    )


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
    from art_negotiation through enach → esign.
    """
    config = {"configurable": {"thread_id": application_id}}

    async def _resume():
        checkpointer = await get_checkpointer()
        graph = build_graph(checkpointer=checkpointer)

        await graph.aupdate_state(
            config,
            values={
                "hitl_decision": hitl_decision.get("decision"),
                "hitl_notes": hitl_decision.get("notes", ""),
                "rm_id": hitl_decision.get("rm_id", ""),
            },
        )

        result = await graph.ainvoke(None, config=config)
        return result

    try:
        result = asyncio.run(_resume())
        decision = hitl_decision.get("decision", "approve")
        final_status = "completed" if decision == "approve" else "rejected"
        _publish_completed(application_id, result, final_status)
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
    """
    Retry disbursement with exponential back-off.
    Schedule: immediate → 1h → 4h → 24h (controlled by max_retries + countdown).

    Simulates an external bank transfer API call. On transient failure it
    re-schedules itself with increasing delay; on final success it publishes
    a pipeline.completed event with final_status='disbursed'.
    """
    attempt = self.request.retries  # 0-indexed

    logger.info(
        "retry_disbursement attempt %d/%d for %s",
        attempt + 1, settings.disbursement_max_retries, application_id,
    )

    # Deterministic simulation — always succeeds.
    # In production, replace with a real bank API call and retry on failure:
    #   resp = httpx.post(BANK_API_URL, json={...}, headers={"Authorization": f"Bearer {token}"})
    #   if resp.status_code != 200:
    #       countdown = [0, 3600, 14400, 86400][min(attempt, 3)]
    #       raise self.retry(countdown=countdown, exc=RuntimeError("Bank transfer failed"))

    # Success — publish disbursed event and update application status via event bus
    disbursement_ref = f"DISB-{application_id[:8].upper()}-{attempt + 1:02d}"
    event_publisher.publish(
        stream="loan:events",
        event_type="pipeline.completed",
        payload={
            "application_id": application_id,
            "stage": "disbursement",
            "final_status": "disbursed",
            "disbursement_ref": disbursement_ref,
            "attempt": attempt + 1,
        },
    )
    logger.info("Disbursement succeeded for %s ref=%s", application_id, disbursement_ref)
    return {"application_id": application_id, "disbursement_ref": disbursement_ref}


@celery_app.task(
    name="agent.run_outreach",
    bind=True,
    max_retries=2,
    default_retry_delay=300,
    queue="agent",
)
def run_outreach(self: Task, payload: dict) -> dict:
    """
    Generate and dispatch a personalised follow-up message for a stale application.
    Triggered directly by the monitoring agent.
    """
    import asyncio
    from agents.outreach.agent import run_outreach as _run_outreach

    try:
        result = asyncio.run(_run_outreach(payload))
        logger.info("Outreach sent for %s (attempt %d)", payload.get("application_id"), payload.get("outreach_attempt", 1))
        return result
    except Exception as exc:
        logger.error("Outreach task failed for %s: %s", payload.get("application_id"), exc)
        raise self.retry(exc=exc)


@celery_app.task(
    name="agent.monitoring_scan",
    queue="agent",
)
def monitoring_scan() -> dict:
    """
    Scheduled task: scan all open applications for staleness and publish
    outreach.required events for any that haven't been updated within threshold.

    Run by Celery Beat every hour.
    """
    from agents.monitoring.agent import run_monitoring_scan
    stale = run_monitoring_scan()
    logger.info("monitoring_scan: %d stale applications flagged", len(stale))
    return {"stale_count": len(stale), "applications": [a["application_id"] for a in stale]}
