from langchain_core.tools import tool


@tool
def check_velocity(phone: str, pan: str) -> dict:
    """Check how many applications were submitted from this phone/PAN in the last 30 days."""
    # TODO: Query DB for recent applications by phone or PAN
    pass


@tool
def check_duplicate_application(pan_number: str) -> dict:
    """Detect if an active application already exists for this PAN."""
    # TODO: Query applications table for existing open applications
    pass


@tool
def run_fraud_model(features: dict) -> float:
    """Run ML fraud scoring model and return risk score 0.0–1.0."""
    # TODO: Call internal or external fraud ML endpoint
    pass
