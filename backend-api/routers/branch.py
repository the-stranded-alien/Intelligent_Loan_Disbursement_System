import os
import uuid
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, HTTPException, UploadFile, File, Form

from db.session import SessionLocal
from db.models import Application
from schemas.application import BranchApplicationCreate
from services.event_publisher import event_publisher

router = APIRouter()


# ── staff fills online form manually ─────────────────────────────────────────
@router.post("/applications", status_code=201)
async def branch_create_application(payload: BranchApplicationCreate):
    """Branch staff submits a typed walk-in application."""
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
            tenure_months=payload.tenure_months or 12,
            status="pending",
            current_stage="lead_capture",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
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
                "lead_source":              "branch_walkin",
                "branch_code":              app.branch_code,
                "branch_name":              app.branch_name,
                "staff_id":                 app.staff_id,
                "staff_name":               app.staff_name,
                "kyc_physically_seen":      app.kyc_physically_seen,
                "customer_consent_signed":  app.customer_consent_signed,
            }
        )
        return {"application_id": app.id, "status": app.status, "stage": app.current_stage}
    finally:
        db.close()


# ── staff scans paper form ─────────────────────────────────────────────
@router.post("/scan", status_code=201)
async def branch_scan_form(
    branch_code:             str = Form(...),
    branch_name:             str = Form(...),
    staff_id:                str = Form(...),
    staff_name:              str = Form(...),
    kyc_physically_seen:     bool = Form(False),
    customer_consent_signed: bool = Form(False),
    file:                    UploadFile = File(...),
):
    """
    Branch staff uploads a scanned paper form image.
    OCR runs inside the lead_capture agent — no fields needed from staff.
    """
    allowed = ["image/jpeg", "image/png", "image/jpg", "application/pdf"]
    if file.content_type not in allowed:
        raise HTTPException(400, f"Unsupported file type: {file.content_type}")

    db = SessionLocal()
    try:
        # Save the scanned image
        file_bytes = await file.read()
        upload_dir = "/app/uploads/scans"
        os.makedirs(upload_dir, exist_ok=True)
        filename = f"scan_{uuid.uuid4()}_{file.filename}"
        file_path = os.path.join(upload_dir, filename)
        with open(file_path, "wb") as f:
            f.write(file_bytes)

        # Placeholder application — OCR will fill the fields
        app = Application(
            id=str(uuid.uuid4()),
            full_name="PENDING_OCR",
            phone="PENDING_OCR",
            email="PENDING_OCR",
            pan_number="PENDING_OCR",
            loan_amount=0.0,
            status="pending",
            current_stage="lead_capture",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            branch_code=branch_code,
            branch_name=branch_name,
            staff_id=staff_id,
            staff_name=staff_name,
            kyc_physically_seen=kyc_physically_seen,
            customer_consent_signed=customer_consent_signed,
            walk_in_timestamp=datetime.now(timezone.utc),
        )
        db.add(app)
        db.commit()
        db.refresh(app)

        # Publish event — all fields empty, OCR will populate them
        event_publisher.publish(
            stream="loan:applications",
            event_type="application.created",
            payload={
                "application_id":           app.id,
                "full_name":                "",
                "phone":                    "",
                "email":                    "",
                "pan_number":               "",
                "loan_amount":              0,
                "loan_purpose":             "",
                "tenure_months":            12,
                "created_at":               str(app.created_at),
                "lead_source":              "branch_walkin_ocr",
                "scanned_document_path":    file_path,
                "scanned_document_mime":    file.content_type,
                "branch_code":              branch_code,
                "branch_name":              branch_name,
                "staff_id":                 staff_id,
                "staff_name":               staff_name,
                "kyc_physically_seen":      kyc_physically_seen,
                "customer_consent_signed":  customer_consent_signed,
            }
        )

        return {
            "application_id": app.id,
            "status":         "pending",
            "stage":          "lead_capture",
            "message":        "Scan received. OCR extraction in progress.",
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
    db = SessionLocal()
    try:
        q = db.query(Application).filter(Application.branch_code != None)
        if branch_code:
            q = q.filter(Application.branch_code == branch_code)
        if staff_id:
            q = q.filter(Application.staff_id == staff_id)
        total = q.count()
        apps = (q.order_by(Application.created_at.desc())
                .offset((page - 1) * page_size)
                .limit(page_size).all())
        return {
            "total": total,
            "items": [
                {
                    "id":          a.id,
                    "full_name":   a.full_name,
                    "loan_amount": a.loan_amount,
                    "status":      a.status,
                    "stage":       a.current_stage,
                    "branch_code": a.branch_code,
                    "staff_id":    a.staff_id,
                    "created_at":  str(a.created_at),
                }
                for a in apps
            ],
        }
    finally:
        db.close()
