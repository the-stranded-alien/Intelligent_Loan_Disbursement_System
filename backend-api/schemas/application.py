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


class BranchApplicationCreate(BaseModel):
    """Schema for branch staff submitting a walk-in application."""
    # Standard applicant fields
    full_name:     str
    phone:         str
    email:         str
    pan_number:    str
    loan_amount:   float
    loan_purpose:  Optional[str] = None
    tenure_months: Optional[int] = None

    # Branch-specific fields
    branch_code:             str
    branch_name:             str
    staff_id:                str
    staff_name:              str
    kyc_physically_seen:     bool = False
    customer_consent_signed: bool = False
    walk_in_timestamp:       Optional[datetime] = None
