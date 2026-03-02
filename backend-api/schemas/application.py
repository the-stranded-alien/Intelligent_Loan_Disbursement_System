from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class ApplicantBase(BaseModel):
    full_name: str
    phone: str
    email: str
    pan_number: str


class LoanRequestBase(BaseModel):
    loan_amount: float
    loan_purpose: str
    tenure_months: int


class ApplicationCreate(ApplicantBase, LoanRequestBase):
    pass


class ApplicationResponse(BaseModel):
    application_id: str
    status: str
    current_stage: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class PipelineStageStatus(BaseModel):
    stage: str
    status: str
    completed_at: Optional[datetime] = None
    decision: Optional[str] = None
    notes: Optional[str] = None
