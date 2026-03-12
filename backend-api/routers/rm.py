import uuid
from datetime import datetime
from fastapi import APIRouter, HTTPException

from db.session import SessionLocal
from db.models import Application, RMReview, AuditLog
from schemas.rm import RMReviewSubmit

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
            app.current_stage = "disbursement"
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
        return {"application_id": application_id, "decision": payload.decision.value, "status": app.status}
    finally:
        db.close()


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
                "id": app.id, "full_name": app.full_name, "email": app.email,
                "phone": app.phone, "pan_number": app.pan_number,
                "loan_amount": app.loan_amount, "loan_purpose": app.loan_purpose,
                "tenure_months": app.tenure_months, "status": app.status,
                "current_stage": app.current_stage,
            },
            "audit_trail": [
                {"event": l.event_type, "actor": l.actor, "payload": l.payload, "at": str(l.created_at)}
                for l in logs
            ],
        }
    finally:
        db.close()
