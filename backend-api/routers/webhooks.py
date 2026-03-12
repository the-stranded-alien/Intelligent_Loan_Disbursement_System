import uuid
from datetime import datetime
from fastapi import APIRouter, Request

from db.session import SessionLocal
from db.models import Application, AuditLog

router = APIRouter()


@router.post("/disburse/callback")
async def disbursement_callback(request: Request):
    body = await request.json()
    application_id = body.get("application_id")
    status = body.get("status")

    if application_id:
        db = SessionLocal()
        try:
            app = db.query(Application).filter(Application.id == application_id).first()
            if app:
                app.status = "disbursed" if status == "success" else "disbursement_failed"
                app.updated_at = datetime.utcnow()
                db.add(AuditLog(
                    id=str(uuid.uuid4()),
                    application_id=application_id,
                    event_type="disbursement_callback",
                    actor="bank-webhook",
                    payload=body,
                    created_at=datetime.utcnow(),
                ))
                db.commit()
        finally:
            db.close()
    return {"received": True}


@router.post("/kyc/callback")
async def kyc_callback(request: Request):
    body = await request.json()
    application_id = body.get("application_id")

    if application_id:
        db = SessionLocal()
        try:
            db.add(AuditLog(
                id=str(uuid.uuid4()),
                application_id=application_id,
                event_type="kyc_callback",
                actor="kyc-provider",
                payload=body,
                created_at=datetime.utcnow(),
            ))
            db.commit()
        finally:
            db.close()
    return {"received": True}
