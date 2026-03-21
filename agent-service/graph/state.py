from typing import TypedDict, Optional, Any
from datetime import datetime


class ApplicationState(TypedDict, total=False):
    # ── Core identity ──────────────────────────────────────────────────────────
    application_id: str
    created_at: str

    # ── Applicant info ─────────────────────────────────────────────────────────
    full_name: str
    phone: str
    email: str
    pan_number: str
    date_of_birth: str
    address: dict[str, Any]

    # ── Loan request ───────────────────────────────────────────────────────────
    loan_amount: float
    loan_purpose: str
    tenure_months: int

    # ── Pipeline stage tracking ────────────────────────────────────────────────
    current_stage: str
    stage_results: dict[str, Any]       # keyed by node name
    pipeline_errors: list[str]

    # ── Lead capture ──────────────────────────────────────────────────────────
    lead_source: str
    lead_score: Optional[float]

    # ── Branch walk-in fields  ─────────────────────────
    branch_code:             Optional[str]
    branch_name:             Optional[str]
    staff_id:                Optional[str]
    staff_name:              Optional[str]
    kyc_physically_seen:     Optional[bool]
    customer_consent_signed: Optional[bool]
    walk_in_timestamp:       Optional[str]

    # ── OCR scan fields ───────────────────────────────────────────────────
    scanned_document_path: Optional[str]    # file path of uploaded image
    scanned_document_mime: Optional[str]    # image/jpeg or image/png
    ocr_extraction_status: Optional[str]    # success | failed | partial
    ocr_extracted_fields:  Optional[dict]   # raw fields dict from OCR service
    ocr_confidence:        Optional[float]  # overall confidence 0.0-1.0

    # ── Lead qualification ────────────────────────────────────────────────────
    qualification_result: Optional[str]  # qualified | rejected
    qualification_notes: str
    disqualification_reasons: list
    employment_type:          Optional[str]
    monthly_income:           Optional[float]

    # ── Identity verification ─────────────────────────────────────────────────
    identity_verified: bool
    identity_provider_response: dict[str, Any]
    kyc_status: str

    # ── Credit assessment ─────────────────────────────────────────────────────
    credit_score: Optional[int]
    credit_bureau_response: dict[str, Any]
    credit_decision: Optional[str]      # approve | reject | manual_review
    suggested_loan_amount: Optional[float]

    # ── Fraud detection ────────────────────────────────────────────────────────
    fraud_risk_score: Optional[float]   # 0.0 – 1.0
    fraud_signals: list[str]
    fraud_decision: Optional[str]       # clear | flag | block

    # ── Compliance ────────────────────────────────────────────────────────────
    compliance_checks: dict[str, bool]  # AML, PEP, sanctions, etc.
    compliance_decision: Optional[str]  # pass | fail
    compliance_notes: str

    # ── Document collection ────────────────────────────────────────────────────
    required_documents: list[str]
    uploaded_documents: list[dict[str, Any]]
    documents_verified: bool
    ocr_results: dict[str, Any]

    # ── Sanction processing ────────────────────────────────────────────────────
    sanction_amount: Optional[float]
    sanction_terms: dict[str, Any]
    hitl_required: bool
    hitl_decision: Optional[str]        # approve | reject | request_info
    hitl_notes: str
    rm_id: Optional[str]

    # ── Disbursement ──────────────────────────────────────────────────────────
    disbursement_status: Optional[str]  # pending | success | failed
    disbursement_reference: Optional[str]
    disbursement_attempts: int
    disbursement_error: Optional[str]

    # ── LLM interaction ────────────────────────────────────────────────────────
    messages: list[dict[str, Any]]      # LangChain message history
    last_llm_response: Optional[str]
