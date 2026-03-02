from langchain_core.tools import tool


@tool
def get_required_documents(loan_type: str, applicant_type: str) -> list[str]:
    """Return the checklist of required documents for a given loan type and applicant."""
    # TODO: Look up document matrix from policy / config
    pass


@tool
def verify_document_completeness(uploaded_docs: list[dict], required_docs: list[str]) -> dict:
    """Check which required documents have been uploaded and verified."""
    # TODO: Compare uploaded list vs required list, return missing and unverified docs
    pass
