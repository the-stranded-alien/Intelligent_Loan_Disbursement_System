from langchain_core.tools import tool


@tool
def check_eligibility_criteria(applicant_data: dict) -> dict:
    """Check basic eligibility: age 21-65, minimum income, loan amount limits."""
    # TODO: Validate age range, income threshold, max loan amount per policy
    pass


@tool
def query_eligibility_policy(query: str) -> str:
    """RAG query to retrieve relevant eligibility policy from pgvector."""
    # TODO: Embed query, similarity search on compliance_policies collection
    pass
