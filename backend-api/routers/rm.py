import math
import uuid
import httpx
from datetime import datetime
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from config.settings import settings
from db.session import SessionLocal
from db.models import Application, RMReview, AuditLog
from schemas.rm import RMReviewSubmit
from services.event_publisher import event_publisher

router = APIRouter()


@router.get("/queue")
async def get_rm_queue():
    db = SessionLocal()
    try:
        apps = db.query(Application).filter(Application.status == "pending_review").all()
        return [
            {
                "application_id": a.id,
                "applicant_name": a.full_name,
                "loan_amount": a.loan_amount,
                "waiting_since": str(a.updated_at),
            }
            for a in apps
        ]
    finally:
        db.close()


@router.post("/{application_id}/review", status_code=201)
async def submit_review(application_id: str, payload: RMReviewSubmit):
    db = SessionLocal()
    try:
        app = db.query(Application).filter(Application.id == application_id).first()
        if not app:
            raise HTTPException(status_code=404, detail="Application not found")

        review = RMReview(
            id=str(uuid.uuid4()),
            application_id=application_id,
            rm_id="rm-system",
            decision=payload.decision.value,
            notes=payload.notes,
            conditions=payload.conditions,
            reviewed_at=datetime.utcnow(),
        )
        db.add(review)

        if payload.decision.value == "approve":
            app.status = "approved"
            app.current_stage = "art_negotiation"
        elif payload.decision.value == "reject":
            app.status = "rejected"
        else:
            app.status = "info_requested"
        app.updated_at = datetime.utcnow()

        db.add(AuditLog(
            id=str(uuid.uuid4()),
            application_id=application_id,
            event_type="rm_review_submitted",
            actor="rm-system",
            payload={"decision": payload.decision.value, "notes": payload.notes},
            created_at=datetime.utcnow(),
        ))
        db.commit()

        # Publish decision to the agent-service HITL consumer so it can
        # enqueue resume_pipeline and continue the LangGraph run.
        event_publisher.publish(
            stream="loan:hitl:decisions",
            event_type="hitl.decision",
            payload={
                "application_id": application_id,
                "decision": payload.decision.value,
                "notes": payload.notes or "",
                "rm_id": "rm-system",
            },
        )

        return {"application_id": application_id, "decision": payload.decision.value, "status": app.status}
    finally:
        db.close()


@router.get("/{application_id}/negotiation-advice")
async def get_negotiation_advice(application_id: str):
    """
    Call agent-service to get offer recommendation advice for the RM.
    Extracts offer data from the audit log (art_negotiation stage result).
    """
    db = SessionLocal()
    try:
        app = db.query(Application).filter(Application.id == application_id).first()
        if not app:
            raise HTTPException(status_code=404, detail="Application not found")

        # Find the art_negotiation stage result from audit logs
        logs = db.query(AuditLog).filter(
            AuditLog.application_id == application_id,
            AuditLog.event_type == "stage.art_negotiation.completed",
        ).order_by(AuditLog.created_at.desc()).first()

        if not logs or not logs.payload:
            raise HTTPException(status_code=404, detail="No offer data found — art_negotiation not yet completed")

        stage_result = logs.payload.get("result", {})
        offers_raw = stage_result.get("offers", [])
        credit_score = stage_result.get("credit_score", 0)

        application_data = {
            "full_name": app.full_name,
            "monthly_income": float(app.monthly_income or 0),
            "existing_emi_amount": float(app.existing_emi_amount or 0),
            "employment_type": app.employment_type or "salaried",
            "loan_amount": float(app.loan_amount or 0),
            "tenure_months": app.tenure_months or 12,
            "credit_score": credit_score,
            "offers": offers_raw,
        }
    finally:
        db.close()

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{settings.agent_service_url}/api/v1/negotiation/analyse",
                json=application_data,
            )
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"Agent service error: {e}")


class CounterOfferRequest(BaseModel):
    rate: float          # annual interest rate %
    tenure_months: int   # repayment period


@router.post("/{application_id}/counter-offer")
async def calculate_counter_offer(application_id: str, payload: CounterOfferRequest):
    """
    RM counter-offer simulator — returns recalculated EMI/totals for a custom
    interest rate and tenure without calling Claude (pure math).
    """
    db = SessionLocal()
    try:
        app = db.query(Application).filter(Application.id == application_id).first()
        if not app:
            raise HTTPException(status_code=404, detail="Application not found")

        # Use sanctioned amount from latest art_negotiation audit log if available
        logs = db.query(AuditLog).filter(
            AuditLog.application_id == application_id,
            AuditLog.event_type == "stage.art_negotiation.completed",
        ).order_by(AuditLog.created_at.desc()).first()

        principal = float(app.loan_amount or 0)
        if logs and logs.payload:
            stage_result = logs.payload.get("result", {})
            principal = float(stage_result.get("sanctioned_amount") or principal)
    finally:
        db.close()

    rate = payload.rate
    n = payload.tenure_months
    if rate <= 0 or n <= 0 or principal <= 0:
        raise HTTPException(status_code=422, detail="rate, tenure_months, and loan amount must be positive")

    monthly_rate = rate / 12 / 100
    emi = principal * monthly_rate * (1 + monthly_rate) ** n / ((1 + monthly_rate) ** n - 1)
    total_payable = emi * n
    processing_fee = round(principal * 0.01, 2)  # 1% flat

    return {
        "principal": round(principal, 2),
        "rate": rate,
        "tenure_months": n,
        "monthly_emi": round(emi, 2),
        "total_payable": round(total_payable, 2),
        "total_interest": round(total_payable - principal, 2),
        "processing_fee": processing_fee,
    }


@router.get("/{application_id}/context")
async def get_review_context(application_id: str):
    db = SessionLocal()
    try:
        app = db.query(Application).filter(Application.id == application_id).first()
        if not app:
            raise HTTPException(status_code=404, detail="Application not found")

        logs = db.query(AuditLog).filter(
            AuditLog.application_id == application_id
        ).order_by(AuditLog.created_at).all()

        return {
            "application": {
                "id": app.id,
                "full_name": app.full_name,
                "email": app.email,
                "phone": app.phone,
                "pan_number": app.pan_number,
                "date_of_birth": app.date_of_birth,
                "employment_type": app.employment_type,
                "monthly_income": app.monthly_income,
                "existing_emi_amount": app.existing_emi_amount,
                "bank_account_number": app.bank_account_number,
                "ifsc_code": app.ifsc_code,
                "loan_amount": app.loan_amount,
                "loan_purpose": app.loan_purpose,
                "tenure_months": app.tenure_months,
                "status": app.status,
                "current_stage": app.current_stage,
            },
            "audit_trail": [
                {"event": l.event_type, "actor": l.actor, "payload": l.payload, "at": str(l.created_at)}
                for l in logs
            ],
        }
    finally:
        db.close()
