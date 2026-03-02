from pydantic import BaseModel
from typing import Optional
from enum import Enum


class ReviewDecision(str, Enum):
    approve = "approve"
    reject = "reject"
    request_info = "request_info"


class RMReviewSubmit(BaseModel):
    decision: ReviewDecision
    notes: Optional[str] = None
    conditions: Optional[list[str]] = None


class RMQueueItem(BaseModel):
    application_id: str
    applicant_name: str
    loan_amount: float
    risk_score: Optional[float] = None
    waiting_since: str
