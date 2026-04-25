from fastapi import APIRouter
from sqlalchemy import func, desc

from db.session import SessionLocal
from db.models import Application, AuditLog, AgentTrace

router = APIRouter()

PIPELINE_STAGES = [
    "lead_capture", "lead_qualification", "identity_verification",
    "credit_assessment", "art_negotiation", "enach", "esign",
]


@router.get("/overview")
async def get_overview():
    db = SessionLocal()
    try:
        total = db.query(func.count(Application.id)).scalar() or 0
        approved = db.query(func.count(Application.id)).filter(Application.status == "approved").scalar() or 0
        rejected = db.query(func.count(Application.id)).filter(Application.status == "rejected").scalar() or 0
        pending = db.query(func.count(Application.id)).filter(Application.status == "pending").scalar() or 0
        total_amount = db.query(func.sum(Application.loan_amount)).filter(Application.status == "approved").scalar() or 0
        return {
            "total_applications": total,
            "approved": approved,
            "rejected": rejected,
            "pending": pending,
            "approval_rate": round(approved / total * 100, 2) if total else 0,
            "total_approved_amount": total_amount,
        }
    finally:
        db.close()


@router.get("/pipeline")
async def get_pipeline_metrics():
    db = SessionLocal()
    try:
        return [
            {
                "stage": stage,
                "applications_at_stage": db.query(func.count(Application.id)).filter(
                    Application.current_stage == stage
                ).scalar() or 0,
            }
            for stage in PIPELINE_STAGES
        ]
    finally:
        db.close()


@router.get("/agents")
async def get_agent_metrics():
    """Per-node rejection rates, HITL queue depth, and average loan amount."""
    db = SessionLocal()
    try:
        stages = []
        for stage in PIPELINE_STAGES:
            at_stage = db.query(func.count(Application.id)).filter(
                Application.current_stage == stage
            ).scalar() or 0
            rejected_here = db.query(func.count(Application.id)).filter(
                Application.current_stage == stage,
                Application.status == "rejected",
            ).scalar() or 0
            stages.append({
                "stage": stage,
                "total_at_stage": at_stage,
                "rejected_at_stage": rejected_here,
                "rejection_rate": round(rejected_here / at_stage * 100, 1) if at_stage else 0.0,
            })
        pending_hitl = db.query(func.count(Application.id)).filter(
            Application.status == "pending_review"
        ).scalar() or 0
        avg_loan = db.query(func.avg(Application.loan_amount)).scalar() or 0.0
        return {
            "stages": stages,
            "pending_hitl_review": pending_hitl,
            "avg_loan_amount": round(float(avg_loan), 2),
        }
    finally:
        db.close()


@router.get("/background-agents")
async def get_background_agent_activity():
    """
    Returns recent activity for all three background agents:
    - Monitoring: outreach.triggered events (app was flagged as stale)
    - Outreach: outreach.sent events (message actually dispatched)
    - Pipeline: stage.*.completed events (node completions across all apps)
    """
    db = SessionLocal()
    try:
        # ── Monitoring agent ──────────────────────────────────────────────────
        monitoring_logs = (
            db.query(AuditLog, Application.full_name)
            .join(Application, AuditLog.application_id == Application.id, isouter=True)
            .filter(AuditLog.event_type == "outreach.triggered")
            .order_by(desc(AuditLog.created_at))
            .limit(20)
            .all()
        )
        monitoring_total = db.query(func.count(AuditLog.id)).filter(
            AuditLog.event_type == "outreach.triggered"
        ).scalar() or 0

        # ── Outreach agent ────────────────────────────────────────────────────
        outreach_logs = (
            db.query(AuditLog, Application.full_name)
            .join(Application, AuditLog.application_id == Application.id, isouter=True)
            .filter(AuditLog.event_type == "outreach.sent")
            .order_by(desc(AuditLog.created_at))
            .limit(20)
            .all()
        )
        outreach_total = db.query(func.count(AuditLog.id)).filter(
            AuditLog.event_type == "outreach.sent"
        ).scalar() or 0

        # ── Pipeline node completions ─────────────────────────────────────────
        pipeline_logs = (
            db.query(AuditLog, Application.full_name)
            .join(Application, AuditLog.application_id == Application.id, isouter=True)
            .filter(AuditLog.event_type.like("stage.%.completed"))
            .order_by(desc(AuditLog.created_at))
            .limit(30)
            .all()
        )
        pipeline_total = db.query(func.count(AuditLog.id)).filter(
            AuditLog.event_type.like("stage.%.completed")
        ).scalar() or 0

        # ── Assessment: apps currently awaiting chat ──────────────────────────
        awaiting_assessment = db.query(func.count(Application.id)).filter(
            Application.status == "info_requested"
        ).scalar() or 0

        def fmt_log(log, full_name):
            return {
                "application_id": log.application_id,
                "full_name": full_name or "Unknown",
                "event_type": log.event_type,
                "actor": log.actor,
                "payload": log.payload or {},
                "at": log.created_at.isoformat() if log.created_at else None,
            }

        return {
            "monitoring": {
                "total_flagged": monitoring_total,
                "recent": [fmt_log(l, n) for l, n in monitoring_logs],
            },
            "outreach": {
                "total_sent": outreach_total,
                "recent": [fmt_log(l, n) for l, n in outreach_logs],
            },
            "pipeline": {
                "total_node_completions": pipeline_total,
                "recent": [fmt_log(l, n) for l, n in pipeline_logs],
            },
            "assessment": {
                "awaiting_chat": awaiting_assessment,
            },
        }
    finally:
        db.close()


@router.get("/evaluation")
async def get_evaluation_metrics():
    """Per-node aggregated metrics from agent_traces: token usage, latency, call count."""
    db = SessionLocal()
    try:
        rows = (
            db.query(
                AgentTrace.node_name,
                AgentTrace.agent_role,
                func.count(AgentTrace.id).label("call_count"),
                func.avg(AgentTrace.duration_ms).label("avg_latency_ms"),
                func.avg(AgentTrace.input_tokens).label("avg_input_tokens"),
                func.avg(AgentTrace.output_tokens).label("avg_output_tokens"),
                func.sum(AgentTrace.input_tokens).label("total_input_tokens"),
                func.sum(AgentTrace.output_tokens).label("total_output_tokens"),
            )
            .group_by(AgentTrace.node_name, AgentTrace.agent_role)
            .order_by(AgentTrace.node_name)
            .all()
        )

        # Pipeline-level stats from application table
        total_apps = db.query(func.count(Application.id)).scalar() or 0
        hitl_apps  = db.query(func.count(Application.id)).filter(
            Application.status.in_(["pending_review", "approved", "completed"])
        ).scalar() or 0
        completed  = db.query(func.count(Application.id)).filter(
            Application.status.in_(["completed", "disbursed"])
        ).scalar() or 0
        rejected   = db.query(func.count(Application.id)).filter(
            Application.status == "rejected"
        ).scalar() or 0

        return {
            "per_node": [
                {
                    "node_name":          r.node_name,
                    "agent_role":         r.agent_role,
                    "call_count":         r.call_count,
                    "avg_latency_ms":     round(float(r.avg_latency_ms or 0), 1),
                    "avg_input_tokens":   round(float(r.avg_input_tokens or 0), 1),
                    "avg_output_tokens":  round(float(r.avg_output_tokens or 0), 1),
                    "total_input_tokens": int(r.total_input_tokens or 0),
                    "total_output_tokens": int(r.total_output_tokens or 0),
                }
                for r in rows
            ],
            "pipeline": {
                "total_applications":  total_apps,
                "hitl_rate_pct":       round(hitl_apps / total_apps * 100, 1) if total_apps else 0,
                "completion_rate_pct": round(completed  / total_apps * 100, 1) if total_apps else 0,
                "rejection_rate_pct":  round(rejected   / total_apps * 100, 1) if total_apps else 0,
            },
        }
    finally:
        db.close()


@router.get("/disbursements")
async def get_disbursement_metrics():
    db = SessionLocal()
    try:
        disbursed = db.query(Application).filter(Application.status == "completed").all()
        total_count = len(disbursed)
        total_amount = sum(a.loan_amount for a in disbursed)
        return {
            "total_disbursed": total_count,
            "total_amount": total_amount,
            "avg_loan_amount": round(total_amount / total_count, 2) if total_count else 0,
        }
    finally:
        db.close()
