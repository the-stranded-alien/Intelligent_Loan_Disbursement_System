from langchain_core.tools import tool


@tool
def aml_screening(name: str, pan: str) -> dict:
    """Screen applicant against AML watchlists."""
    # TODO: Query AML database / third-party screening API
    pass


@tool
def pep_screening(name: str, date_of_birth: str) -> dict:
    """Screen applicant against Politically Exposed Persons list."""
    # TODO: Query PEP database
    pass


@tool
def sanctions_check(name: str, pan: str) -> dict:
    """Check applicant against OFAC and other sanctions lists."""
    # TODO: Query sanctions database
    pass


@tool
def query_rbi_policy(query: str) -> str:
    """RAG query for RBI lending guidelines and compliance requirements."""
    # TODO: Vector similarity search on compliance_policies collection
    pass
