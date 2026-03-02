from langchain_core.tools import tool


@tool
def initiate_bank_transfer(
    account_number: str,
    ifsc_code: str,
    amount: float,
    reference_id: str,
) -> dict:
    """Initiate NEFT/IMPS transfer via payment gateway."""
    # TODO: Call bank API / payment gateway, return transaction_id and status
    pass


@tool
def verify_disbursement_status(transaction_id: str) -> dict:
    """Poll payment gateway for the status of a disbursement transaction."""
    # TODO: Call payment API status endpoint, return confirmed/pending/failed
    pass
