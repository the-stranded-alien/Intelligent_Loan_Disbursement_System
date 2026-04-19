from typing import TypedDict, Optional, Any


class ApplicationState(TypedDict, total=False):
    # ── Core identity ──────────────────────────────────────────────────────────
    application_id: str
    created_at: str

    # ── Applicant info (web form) ──────────────────────────────────────────────
    full_name: str
    phone: str
    email: str
    pan_number: str
    date_of_birth: str          # YYYY-MM-DD
    city: str
    state: str
    residential_status: str     # owned | rented | family
    years_at_current_address: int
    employment_type: str        # salaried | self_employed | business
    employer_name: str
    years_in_current_job: int
    monthly_income: float       # declared monthly income in ₹
    existing_emi_amount: float  # current monthly EMI obligations in ₹

    # ── Loan request ───────────────────────────────────────────────────────────
    loan_amount: float
    loan_purpose: str
    tenure_months: int

    # ── Pipeline stage tracking ────────────────────────────────────────────────
    current_stage: str
    stage_results: dict[str, Any]   # keyed by node name
    pipeline_errors: list[str]

    # ── Node 1: Lead Capture ───────────────────────────────────────────────────
    lead_source: str
    eligibility_result: Optional[str]   # eligible | ineligible
    eligibility_reason: str
    data_quality_issues: list[str]

    # ── Node 2: Lead Qualification ────────────────────────────────────────────
    qualification_result: Optional[str]   # pass | fail | request_info
    qualification_notes: str
    verified_income: Optional[float]      # income verified from docs
    max_eligible_amount: Optional[float]  # max loan based on income ratio

    # ── Node 3: Identity Verification ─────────────────────────────────────────
    identity_verified: bool
    pan_verified: bool
    name_match: bool
    kyc_status: str                         # verified | failed | mismatch

    # ── Node 4: Credit Assessment ─────────────────────────────────────────────
    credit_score: Optional[int]             # 300–900
    credit_decision: Optional[str]          # approve | reject
    suggested_loan_amount: Optional[float]
    repayment_history: str                  # good | fair | poor

    # ── Node 5: ART Negotiation ───────────────────────────────────────────────
    negotiation_offers: list[dict[str, Any]]  # 2-3 offer options
    selected_offer: Optional[dict[str, Any]]
    sanctioned_amount: Optional[float]
    interest_rate_percent: Optional[float]
    monthly_emi: Optional[float]
    total_payable: Optional[float]
    processing_fee: Optional[float]
    # HITL fields (reused by art_negotiation)
    hitl_required: bool
    hitl_decision: Optional[str]    # approve | reject | request_info
    hitl_notes: str
    rm_id: Optional[str]

    # ── Node 6: e-NACH ────────────────────────────────────────────────────────
    enach_status: Optional[str]     # success | failed | pending
    enach_reference: Optional[str]
    mandate_id: Optional[str]
    bank_account_number: Optional[str]
    ifsc_code: Optional[str]

    # ── Node 7: E-Sign ────────────────────────────────────────────────────────
    esign_status: Optional[str]     # success | failed
    esign_reference: Optional[str]
    agreement_url: Optional[str]
    signed_at: Optional[str]

    # ── Node 8: Disbursement ──────────────────────────────────────────────────
    disbursement_status: Optional[str]     # success | failed | pending
    disbursement_reference: Optional[str]
    disbursement_attempts: int

    # ── LLM interaction ────────────────────────────────────────────────────────
    messages: list[dict[str, Any]]
    last_llm_response: Optional[str]
