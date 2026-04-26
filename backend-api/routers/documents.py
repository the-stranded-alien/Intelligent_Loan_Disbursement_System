import os
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, UploadFile, File, Form

from db.session import SessionLocal
from db.models import Document, Application, AuditLog
from config.settings import settings
from services.event_publisher import event_publisher
from services.websocket_manager import websocket_manager

router = APIRouter()


@router.post("/{application_id}/upload", status_code=201)
async def upload_document(
    application_id: str,
    document_type: str = Form(...),
    file: UploadFile = File(...),
):
    db = SessionLocal()
    try:
        app = db.query(Application).filter(Application.id == application_id).first()
        if not app:
            raise HTTPException(status_code=404, detail="Application not found")

        # Save file (use /tmp as fallback so Railway ephemeral filesystem doesn't break uploads)
        base_dir = getattr(settings, "local_storage_path", "/tmp/loan_docs")
        upload_dir = os.path.join(base_dir, application_id)
        os.makedirs(upload_dir, exist_ok=True)
        filename = f"{uuid.uuid4()}_{file.filename or 'upload'}"
        file_path = os.path.join(upload_dir, filename)
        with open(file_path, "wb") as f:
            f.write(await file.read())

        doc = Document(
            id=str(uuid.uuid4()),
            application_id=application_id,
            document_type=document_type,
            storage_path=file_path,
            verification_status="pending",
            created_at=datetime.utcnow(),
        )
        db.add(doc)

        # KYC gate: only resume the pipeline when status is kyc_pending, meaning
        # the repayment assessment has already been completed. If status is
        # info_requested the assessment is still required first — the doc is
        # saved but the pipeline stays paused.
        kyc_triggered = False
        if app.status == "kyc_pending":
            app.status = "processing"
            app.current_stage = "identity_verification"
            app.updated_at = datetime.now(timezone.utc)
            db.add(AuditLog(
                id=str(uuid.uuid4()),
                application_id=application_id,
                event_type="kyc.docs_submitted",
                actor="applicant",
                payload={"document_type": document_type, "filename": filename},
                created_at=datetime.now(timezone.utc),
            ))
            # Mark identity_verification as completed in the timeline immediately
            # so the UI updates without waiting for the pipeline event round-trip.
            db.add(AuditLog(
                id=str(uuid.uuid4()),
                application_id=application_id,
                event_type="stage.identity_verification.completed",
                actor="kyc-gate",
                payload={"stage": "identity_verification", "result": {
                    "kyc_status": "verified",
                    "document_type": document_type,
                    "note": "KYC document submitted by applicant",
                }},
                created_at=datetime.now(timezone.utc),
            ))
            kyc_triggered = True

        db.commit()
        db.refresh(doc)

        if kyc_triggered:
            # Resume pipeline from identity_verification interrupt.
            event_publisher.publish(
                stream="loan:hitl:decisions",
                event_type="hitl.decision",
                payload={
                    "application_id": application_id,
                    "decision": "approve",
                    "notes": f"KYC documents submitted ({document_type})",
                    "rm_id": "kyc-gate",
                },
            )
            # Broadcast node.completed for identity_verification so the live
            # timeline ticks to "verified" before the pipeline event arrives.
            await websocket_manager.broadcast(application_id, {
                "event": "node.completed",
                "stage": "identity_verification",
                "data": {"stage": "identity_verification"},
            })
            await websocket_manager.broadcast(application_id, {
                "event": "kyc_docs_submitted",
                "document_type": document_type,
                "message": "KYC documents received. Identity verification is now running.",
            })

        return {
            "document_id": doc.id,
            "document_type": doc.document_type,
            "verification_status": doc.verification_status,
            "kyc_triggered": kyc_triggered,
        }
    finally:
        db.close()


@router.get("/{application_id}")
async def list_documents(application_id: str):
    db = SessionLocal()
    try:
        docs = db.query(Document).filter(Document.application_id == application_id).all()
        return [
            {
                "id": d.id,
                "document_type": d.document_type,
                "verification_status": d.verification_status,
                "created_at": str(d.created_at),
            }
            for d in docs
        ]
    finally:
        db.close()


@router.delete("/{document_id}", status_code=204)
async def delete_document(document_id: str):
    db = SessionLocal()
    try:
        doc = db.query(Document).filter(Document.id == document_id).first()
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")
        db.delete(doc)
        db.commit()
    finally:
        db.close()
