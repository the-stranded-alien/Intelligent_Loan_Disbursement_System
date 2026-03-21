from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import uuid
from datetime import datetime, timezone

from db.session import SessionLocal
from db.models import Application, AuditLog
from services.event_publisher import event_publisher

router = APIRouter()


class ApplicationCreate(BaseModel):
    full_name: str
    phone: str
    email: str
    pan_number: str
    loan_amount: float
    loan_purpose: str | None = None
    tenure_months: int | None = None


@router.post("/")
async def create_application(payload: ApplicationCreate):
    db = SessionLocal()
    try:
        app = Application(
            id=str(uuid.uuid4()),
            full_name=payload.full_name,
            phone=payload.phone,
            email=payload.email,
            pan_number=payload.pan_number,
            loan_amount=payload.loan_amount,
            loan_purpose=payload.loan_purpose,
            tenure_months=payload.tenure_months,
            status="pending",
            current_stage="lead_capture",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            date_of_birth=payload.date_of_birth,       # ADD
            employment_type=payload.employment_type,   # ADD
            monthly_income=payload.monthly_income,     # ADD
        )
        db.add(app)
        db.commit()
        db.refresh(app)

        event_publisher.publish(
            stream="loan:applications",
            event_type="application.created",
            payload={
                "application_id": app.id,
                "full_name": app.full_name,
                "phone": app.phone,
                "email": app.email,
                "pan_number": app.pan_number,
                "loan_amount": app.loan_amount,
                "loan_purpose": app.loan_purpose or "",
                "tenure_months": app.tenure_months or 12,
                "created_at": str(app.created_at),
                "date_of_birth":   payload.date_of_birth,      # ADD
                "employment_type": payload.employment_type,    # ADD
                "monthly_income":  payload.monthly_income,     # ADD
            }
        )

        return {"application_id": app.id, "status": app.status, "stage": app.current_stage}
    finally:
        db.close()


@router.get("/")
async def list_applications(
    page: int = 1,
    page_size: int = 10,
    status: str | None = None,
    search: str | None = None,
):
    db = SessionLocal()
    try:
        q = db.query(Application)
        if status:
            q = q.filter(Application.status == status)
        if search:
            term = f"%{search}%"
            q = q.filter(
                Application.full_name.ilike(term)
                | Application.email.ilike(term)
                | Application.pan_number.ilike(term)
            )
        total = q.count()
        apps = q.order_by(Application.created_at.desc()).offset(
            (page - 1) * page_size).limit(page_size).all()
        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": max(1, (total + page_size - 1) // page_size),
            "items": [
                {
                    "id": a.id, "full_name": a.full_name, "email": a.email,
                    "pan_number": a.pan_number, "loan_amount": a.loan_amount,
                    "loan_purpose": a.loan_purpose, "tenure_months": a.tenure_months,
                    "status": a.status, "stage": a.current_stage, "created_at": str(a.created_at),
                }
                for a in apps
            ],
        }
    finally:
        db.close()


@router.get("/{application_id}/status")
async def get_application_status(application_id: str):
    db = SessionLocal()
    try:
        app = db.query(Application).filter(
            Application.id == application_id).first()
        if not app:
            raise HTTPException(
                status_code=404, detail="Application not found")
        return {
            "application_id": app.id,
            "full_name": app.full_name,
            "loan_amount": app.loan_amount,
            "loan_purpose": app.loan_purpose,
            "tenure_months": app.tenure_months,
            "status": app.status,
            "current_stage": app.current_stage,
            "updated_at": str(app.updated_at),
            "created_at": str(app.created_at),
        }
    finally:
        db.close()


@router.get("/{application_id}/events")
async def get_application_events(application_id: str):
    db = SessionLocal()
    try:
        app = db.query(Application).filter(
            Application.id == application_id).first()
        if not app:
            raise HTTPException(
                status_code=404, detail="Application not found")
        logs = (
            db.query(AuditLog)
            .filter(AuditLog.application_id == application_id)
            .order_by(AuditLog.created_at)
            .all()
        )
        return [
            {"event": l.event_type, "actor": l.actor,
                "payload": l.payload, "at": str(l.created_at)}
            for l in logs
        ]
    finally:
        db.close()


@router.get("/{application_id}")
async def get_application(application_id: str):
    db = SessionLocal()
    try:
        app = db.query(Application).filter(
            Application.id == application_id).first()
        if not app:
            raise HTTPException(
                status_code=404, detail="Application not found")
        return {
            "id": app.id, "full_name": app.full_name, "phone": app.phone,
            "email": app.email, "pan_number": app.pan_number,
            "loan_amount": app.loan_amount, "loan_purpose": app.loan_purpose,
            "tenure_months": app.tenure_months, "status": app.status,
            "stage": app.current_stage, "created_at": str(app.created_at),
        }
    finally:
        db.close()
