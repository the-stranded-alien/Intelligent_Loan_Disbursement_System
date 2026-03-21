import uuid
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, HTTPException

from db.session import SessionLocal
from db.models import Application
from schemas.application import BranchApplicationCreate
from services.event_publisher import event_publisher

router = APIRouter()


@router.post("/applications", status_code=201)
async def branch_create_application(payload: BranchApplicationCreate):
    """Branch staff submits a walk-in loan application."""
    db = SessionLocal()
    try:
        app = Application(
            id=str(uuid.uuid4()),
            # Standard fields
            full_name=payload.full_name,
            phone=payload.phone,
            email=payload.email,
            pan_number=payload.pan_number,
            loan_amount=payload.loan_amount,
            loan_purpose=payload.loan_purpose,
            tenure_months=payload.tenure_months or 12,
            status="pending",
            current_stage="lead_capture",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            # Branch fields
            branch_code=payload.branch_code,
            branch_name=payload.branch_name,
            staff_id=payload.staff_id,
            staff_name=payload.staff_name,
            kyc_physically_seen=payload.kyc_physically_seen,
            customer_consent_signed=payload.customer_consent_signed,
            walk_in_timestamp=payload.walk_in_timestamp or datetime.now(
                timezone.utc),
        )
        db.add(app)
        db.commit()
        db.refresh(app)

        # Same Redis stream as web portal — pipeline is identical
        event_publisher.publish(
            stream="loan:applications",
            event_type="application.created",
            payload={
                "application_id":           app.id,
                "full_name":                app.full_name,
                "phone":                    app.phone,
                "email":                    app.email,
                "pan_number":               app.pan_number,
                "loan_amount":              app.loan_amount,
                "loan_purpose":             app.loan_purpose or "",
                "tenure_months":            app.tenure_months,
                "created_at":               str(app.created_at),
                # Branch metadata
                "lead_source":              "branch_walkin",
                "branch_code":              app.branch_code,
                "branch_name":              app.branch_name,
                "staff_id":                 app.staff_id,
                "staff_name":               app.staff_name,
                "kyc_physically_seen":      app.kyc_physically_seen,
                "customer_consent_signed":  app.customer_consent_signed,
                "walk_in_timestamp":        str(app.walk_in_timestamp),
            }
        )

        return {
            "application_id": app.id,
            "status":         app.status,
            "stage":          app.current_stage,
            "branch_code":    app.branch_code,
            "staff_id":       app.staff_id,
        }

    finally:
        db.close()


@router.get("/applications")
async def branch_list_applications(
    branch_code: Optional[str] = None,
    staff_id:    Optional[str] = None,
    page:        int = 1,
    page_size:   int = 20,
):
    """List applications submitted by a specific branch or staff member."""
    db = SessionLocal()
    try:
        q = db.query(Application).filter(
            Application.branch_code != None
        )
        if branch_code:
            q = q.filter(Application.branch_code == branch_code)
        if staff_id:
            q = q.filter(Application.staff_id == staff_id)

        total = q.count()
        apps = (q.order_by(Application.created_at.desc())
                 .offset((page - 1) * page_size)
                 .limit(page_size)
                 .all())

        return {
            "total": total,
            "items": [
                {
                    "id":           a.id,
                    "full_name":    a.full_name,
                    "loan_amount":  a.loan_amount,
                    "status":       a.status,
                    "stage":        a.current_stage,
                    "branch_code":  a.branch_code,
                    "staff_id":     a.staff_id,
                    "created_at":   str(a.created_at),
                }
                for a in apps
            ],
        }
    finally:
        db.close()
