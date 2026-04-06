from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class ApplicationCreate(BaseModel):
    # Applicant identity
    full_name: str
    phone: str
    email: str
    pan_number: str
    date_of_birth: Optional[str] = None
    # Financial profile
    employment_type: Optional[str] = "salaried"
    monthly_income: Optional[float] = 0.0
    existing_emi_amount: Optional[float] = 0.0
    bank_account_number: Optional[str] = None
    ifsc_code: Optional[str] = None
    # Loan request
    loan_amount: float
    loan_purpose: Optional[str] = None
    tenure_months: Optional[int] = 12


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
