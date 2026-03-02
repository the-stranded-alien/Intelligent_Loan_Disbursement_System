from langchain_core.tools import tool


@tool
def normalize_phone(phone: str) -> str:
    """Normalize an Indian phone number to E.164 format."""
    # TODO: Strip country code, validate 10-digit number, return +91XXXXXXXXXX
    pass


@tool
def score_lead(applicant_data: dict) -> float:
    """Compute an initial lead score (0–100) based on applicant profile."""
    # TODO: Apply scoring heuristics (loan amount, purpose, completeness of data)
    pass
