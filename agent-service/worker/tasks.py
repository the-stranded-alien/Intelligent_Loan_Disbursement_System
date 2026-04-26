import asyncio
import logging
from celery import Task
from worker.celery_app import celery_app
from config.settings import settings
from graph.graph import build_graph
from graph.checkpointer import get_checkpointer
from graph.state import ApplicationState
from services.event_publisher import event_publisher
from agents.monitoring.agent import run_monitoring_scan
from agents.outreach.agent import run_outreach as _run_outreach_agent

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

        # First ainvoke — runs Nodes 1–2 (lead_capture + lead_qualification)
        # then pauses before identity_verification.
        # If pipeline rejects at Node 1 (ineligible) the graph ends instead.
        result = await graph.ainvoke(initial_state, config=config)
        snapshot = await graph.aget_state(config)
        next_nodes = set(snapshot.next or [])

        if "identity_verification" in next_nodes:
            # Assessment is always required before KYC runs — this ensures the
            # repayment chat is never skipped even when qualification returns "pass".
            event_publisher.publish(
                stream="loan:events",
                event_type="assessment_required",
                payload={
                    "application_id": application_id,
                    "stage_results": result.get("stage_results", {}),
                },
            )
            logger.info("Pipeline paused for assessment: %s", application_id)
            return result

        if "art_negotiation" in next_nodes:
            loan_amount = result.get("loan_amount", 0)
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
        elif not next_nodes:
            # Graph reached END — rejected early (ineligible / hard fail).
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
    """Resume a pipeline that was interrupted at identity_verification (after
    assessment) or at art_negotiation (after RM HITL review).

    Checks the current interrupt point before injecting state so that an
    assessment-approval resume doesn't pre-fill hitl_decision and bypass the
    RM gate on large loans.
    """
    config = {"configurable": {"thread_id": application_id}}

    async def _resume():
        checkpointer = await get_checkpointer()
        graph = build_graph(checkpointer=checkpointer)

        snapshot = await graph.aget_state(config)
        current_next = set(snapshot.next or [])

        if "art_negotiation" in current_next:
            # RM HITL resume — inject decision so route_after_art can see it.
            await graph.aupdate_state(
                config,
                values={
                    "hitl_decision": hitl_decision.get("decision"),
                    "hitl_notes": hitl_decision.get("notes", ""),
                    "rm_id": hitl_decision.get("rm_id", ""),
                },
            )
            result = await graph.ainvoke(None, config=config)
            decision = hitl_decision.get("decision", "approve")
            final_status = "completed" if decision == "approve" else "rejected"
            _publish_completed(application_id, result, final_status)
            return result

        # Assessment resume — paused at identity_verification.
        # Do NOT inject hitl_decision here; that field is for RM HITL only.
        result = await graph.ainvoke(None, config=config)
        snapshot = await graph.aget_state(config)
        next_nodes = set(snapshot.next or [])

        if "art_negotiation" in next_nodes:
            loan_amount = result.get("loan_amount", 0)
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
                logger.info("Pipeline paused for HITL after assessment: %s", application_id)
                return result
            # Small loan — continue through art → enach → esign.
            result = await graph.ainvoke(None, config=config)

        _publish_completed(application_id, result, "completed")
        return result

    try:
        result = asyncio.run(_resume())
        logger.info("Pipeline resumed for %s, stage=%s", application_id, result.get("current_stage"))
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
    try:
        result = asyncio.run(_run_outreach_agent(payload))
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

    Run by Celery Beat every 2 minutes.
    """
    stale = run_monitoring_scan()
    logger.info("monitoring_scan: %d stale applications flagged", len(stale))
    return {"stale_count": len(stale), "applications": [a["application_id"] for a in stale]}
