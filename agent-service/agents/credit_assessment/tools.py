from langchain_core.tools import tool


@tool
def fetch_credit_report(pan_number: str) -> dict:
    """Fetch credit bureau report from CIBIL/Experian for the given PAN."""
    # TODO: Call credit bureau API, return score, history, existing loans
    pass


@tool
def calculate_dti_ratio(monthly_income: float, existing_emi: float, proposed_emi: float) -> float:
    """Calculate Debt-to-Income ratio."""
    # TODO: (existing_emi + proposed_emi) / monthly_income * 100
    pass
