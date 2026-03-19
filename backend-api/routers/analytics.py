from fastapi import APIRouter
from sqlalchemy import func

from db.session import SessionLocal
from db.models import Application

router = APIRouter()

PIPELINE_STAGES = [
    "lead_capture", "lead_qualification", "identity_verification",
    "credit_assessment", "fraud_detection", "compliance",
    "document_collection", "sanction_processing", "disbursement",
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


@router.get("/disbursements")
async def get_disbursement_metrics():
    db = SessionLocal()
    try:
        disbursed = db.query(Application).filter(Application.status == "disbursed").all()
        total_count = len(disbursed)
        total_amount = sum(a.loan_amount for a in disbursed)
        return {
            "total_disbursed": total_count,
            "total_amount": total_amount,
            "avg_loan_amount": round(total_amount / total_count, 2) if total_count else 0,
        }
    finally:
        db.close()
