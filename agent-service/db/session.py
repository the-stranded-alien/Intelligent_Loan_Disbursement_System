"""
Lightweight SQLAlchemy session for the agent-service.
Only used by background agents (e.g. monitoring) that need direct DB access.
The schema is owned by backend-api — agent-service only reads/queries.
"""

from sqlalchemy import create_engine, Column, String, Float, Integer, DateTime, Text, JSON, ForeignKey
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from datetime import datetime
import uuid

from config.settings import settings

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_size=2,
    max_overflow=2,
)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


class Base(DeclarativeBase):
    pass


# ── Minimal model mirrors (read-only, no migrations here) ──────────────────

class Application(Base):
    __tablename__ = "applications"

    id = Column(String, primary_key=True)
    full_name = Column(String)
    phone = Column(String)
    email = Column(String)
    pan_number = Column(String)
    loan_amount = Column(Float)
    loan_purpose = Column(String)
    tenure_months = Column(Integer)
    status = Column(String)
    current_stage = Column(String)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    application_id = Column(String, ForeignKey("applications.id"))
    event_type = Column(String)
    actor = Column(String)
    payload = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
