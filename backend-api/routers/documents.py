import os
import uuid
from datetime import datetime
from fastapi import APIRouter, HTTPException, UploadFile, File, Form

from db.session import SessionLocal
from db.models import Document, Application
from config.settings import settings

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

        upload_dir = os.path.join(settings.local_storage_path, application_id)
        os.makedirs(upload_dir, exist_ok=True)
        filename = f"{uuid.uuid4()}_{file.filename}"
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
        db.commit()
        db.refresh(doc)
        return {
            "document_id": doc.id,
            "document_type": doc.document_type,
            "verification_status": doc.verification_status,
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
