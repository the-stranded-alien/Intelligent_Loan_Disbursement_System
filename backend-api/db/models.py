from sqlalchemy import Column, String, Float, Integer, DateTime, Text, JSON, ForeignKey
from sqlalchemy.orm import DeclarativeBase, relationship
from datetime import datetime
import uuid


class Base(DeclarativeBase):
    pass


class Application(Base):
    __tablename__ = "applications"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    # Applicant info
    full_name = Column(String, nullable=False)
    phone = Column(String, nullable=False)
    email = Column(String, nullable=False)
    pan_number = Column(String, nullable=False)
    date_of_birth = Column(String,  nullable=True)
    employment_type = Column(String,  nullable=True)
    monthly_income = Column(Float,   nullable=True)
    # Loan info
    loan_amount = Column(Float, nullable=False)
    loan_purpose = Column(String)
    tenure_months = Column(Integer)
    # Pipeline state
    status = Column(String, default="pending")
    current_stage = Column(String)
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow,
                        onupdate=datetime.utcnow)
    # ── Branch walk-in fields ───
    branch_code = Column(String,  nullable=True)
    branch_name = Column(String,  nullable=True)
    staff_id = Column(String,  nullable=True)
    staff_name = Column(String,  nullable=True)
    kyc_physically_seen = Column(Boolean, default=False)
    customer_consent_signed = Column(Boolean, default=False)
    walk_in_timestamp = Column(DateTime, nullable=True)


class Document(Base):
    __tablename__ = "documents"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    application_id = Column(String, ForeignKey(
        "applications.id"), nullable=False)
    document_type = Column(String, nullable=False)
    storage_path = Column(String, nullable=False)
    ocr_result = Column(JSON)
    verification_status = Column(String, default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)


class RMReview(Base):
    __tablename__ = "rm_reviews"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    application_id = Column(String, ForeignKey(
        "applications.id"), nullable=False)
    rm_id = Column(String, nullable=False)
    decision = Column(String, nullable=False)
    notes = Column(Text)
    conditions = Column(JSON)
    reviewed_at = Column(DateTime, default=datetime.utcnow)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    application_id = Column(String, ForeignKey("applications.id"))
    event_type = Column(String, nullable=False)
    actor = Column(String)
    payload = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
