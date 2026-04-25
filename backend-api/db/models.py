from sqlalchemy import Column, String, Float, Integer, DateTime, Text, JSON, ForeignKey, Index
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
    date_of_birth = Column(String)                    # YYYY-MM-DD
    city = Column(String)
    state = Column(String)
    residential_status = Column(String)               # owned | rented | family
    years_at_current_address = Column(Integer)
    employment_type = Column(String, default="salaried")  # salaried | self_employed | business
    employer_name = Column(String)
    years_in_current_job = Column(Integer)
    monthly_income = Column(Float, default=0.0)
    existing_emi_amount = Column(Float, default=0.0)
    bank_account_number = Column(String)
    ifsc_code = Column(String)
    # Loan info
    loan_amount = Column(Float, nullable=False)
    loan_purpose = Column(String)
    tenure_months = Column(Integer)
    # Pipeline state
    status = Column(String, default="pending")
    current_stage = Column(String)
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Document(Base):
    __tablename__ = "documents"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    application_id = Column(String, ForeignKey("applications.id"), nullable=False)
    document_type = Column(String, nullable=False)
    storage_path = Column(String, nullable=False)
    ocr_result = Column(JSON)
    verification_status = Column(String, default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)


class RMReview(Base):
    __tablename__ = "rm_reviews"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    application_id = Column(String, ForeignKey("applications.id"), nullable=False)
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


class AgentTrace(Base):
    __tablename__ = "agent_traces"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    application_id = Column(String, ForeignKey("applications.id"), nullable=True)
    agent_role = Column(String, nullable=False)   # planner | analyst | critic | coordinator
    node_name = Column(String, nullable=False)
    prompt_rendered = Column(Text)
    raw_llm_response = Column(Text)
    parsed_output = Column(JSON)
    duration_ms = Column(Integer)
    model = Column(String)
    input_tokens = Column(Integer)
    output_tokens = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
