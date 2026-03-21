from langchain_core.tools import tool


@tool
def normalize_phone(phone: str) -> str:
    """Normalize an Indian phone number to E.164 format."""
    import re

    if not phone:
        return phone

    # Strip spaces, dashes, dots, brackets
    cleaned = re.sub(r"[\s\-\.\(\)]", "", phone)

    # Strip leading + sign before processing
    cleaned = cleaned.lstrip("+")

    # Handle country code variations
    if cleaned.startswith("91") and len(cleaned) == 12:
        cleaned = cleaned[2:]
    elif cleaned.startswith("0") and len(cleaned) == 11:
        cleaned = cleaned[1:]

    # Validate: 10 digits starting with 6, 7, 8, or 9
    if re.fullmatch(r"[6-9]\d{9}", cleaned):
        return f"+91{cleaned}"

    # Could not normalize — return original so Claude can flag it
    return phone


@tool
def score_lead(applicant_data: dict) -> float:
    """Compute an initial lead score (0–100) based on applicant profile."""
    score = 0.0

    # Data completeness (50 pts)
    required_fields = ["full_name", "phone",
                       "email", "pan_number", "loan_amount"]
    for field in required_fields:
        if applicant_data.get(field):
            score += 10

    # Loan amount range (20 pts)
    loan = applicant_data.get("loan_amount", 0)
    if 100_000 <= loan <= 2_500_000:
        score += 20
    elif 50_000 <= loan < 100_000:
        score += 10
    elif loan > 2_500_000:
        score += 15

    # Phone validity (15 pts)
    import re
    phone = applicant_data.get("phone", "")
    cleaned = re.sub(r"[\s\-\+]", "", phone)
    if cleaned.startswith("91"):
        cleaned = cleaned[2:]
    if re.fullmatch(r"[6-9]\d{9}", cleaned):
        score += 15

    # Email present (10 pts)
    email = applicant_data.get("email", "")
    if email and "@" in email and "." in email.split("@")[-1]:
        score += 10

    # PAN format valid (5 pts)
    pan = applicant_data.get("pan_number", "")
    if re.fullmatch(r"[A-Z]{5}[0-9]{4}[A-Z]", pan.upper()):
        score += 5

    # ── Branch walk-in bonus ──────────────────────────────
    if applicant_data.get("lead_source") == "branch_walkin":
        score += 15
    if applicant_data.get("kyc_physically_seen"):
        score += 10
    if applicant_data.get("customer_consent_signed"):
        score += 5

    return round(min(score, 100.0), 1)
