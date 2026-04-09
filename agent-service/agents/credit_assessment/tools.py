import hashlib


# CIBIL score tool — no langchain dependency, uses Anthropic tool_use format directly

CIBIL_TOOL_SCHEMA = {
    "name": "mock_cibil_lookup",
    "description": (
        "Fetch a simulated CIBIL / Experian credit bureau report for the given PAN number. "
        "Returns credit score (300-900), active loan count, overdue payments, and credit age in months. "
        "Call this tool first before making any credit decision."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "pan_number": {
                "type": "string",
                "description": "The applicant's PAN number (e.g. ABCDE1234F)",
            }
        },
        "required": ["pan_number"],
    },
}


def mock_cibil_lookup(pan_number: str) -> dict:
    """
    Deterministic mock CIBIL lookup.
    Derives a stable score from the PAN hash so the same applicant
    always gets the same score, but different applicants get different scores.

    Score bands:
      hash % 10 in {0,1}   → 720–780  (good)
      hash % 10 in {2,3,4} → 650–719  (fair)
      hash % 10 in {5,6}   → 600–649  (borderline)
      hash % 10 in {7,8,9} → 750–820  (excellent)
    """
    digest = int(hashlib.sha256(pan_number.upper().encode()).hexdigest(), 16)
    bucket = digest % 10

    if bucket in (7, 8, 9):
        score = 750 + (digest % 71)          # 750–820 excellent
        overdue = 0
        active_loans = digest % 2
        credit_age_months = 60 + (digest % 60)
    elif bucket in (0, 1):
        score = 720 + (digest % 61)          # 720–780 good
        overdue = 0
        active_loans = digest % 3
        credit_age_months = 36 + (digest % 48)
    elif bucket in (2, 3, 4):
        score = 650 + (digest % 70)          # 650–719 fair
        overdue = digest % 2
        active_loans = 1 + digest % 3
        credit_age_months = 24 + (digest % 36)
    else:
        score = 600 + (digest % 50)          # 600–649 borderline
        overdue = 1 + digest % 3
        active_loans = 2 + digest % 3
        credit_age_months = 12 + (digest % 24)

    return {
        "pan_number": pan_number.upper(),
        "credit_score": int(score),
        "active_loan_count": int(active_loans),
        "overdue_payments_last_12m": int(overdue),
        "credit_age_months": int(credit_age_months),
        "bureau": "CIBIL",
        "status": "success",
    }
