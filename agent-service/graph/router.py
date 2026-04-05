from langgraph.graph import END
from graph.state import ApplicationState


def route_after_lead_capture(state: ApplicationState) -> str:
    """Node 1 → Node 2 or END.
    Only eligible applicants proceed to document verification.
    """
    if state.get("eligibility_result") == "eligible":
        return "qualify"
    return "reject"


def route_after_qualification(state: ApplicationState) -> str:
    """Node 2 → Node 3 or END.
    Only applicants with verified documents proceed to KYC.
    request_info also halts — applicant must resubmit.
    """
    result = state.get("qualification_result", "fail")
    if result == "pass":
        return "continue"
    return "reject"


def route_after_identity(state: ApplicationState) -> str:
    """Node 3 → Node 4 or END.
    PAN must be verified and name must match.
    """
    if state.get("identity_verified") and state.get("kyc_status") == "verified":
        return "continue"
    return "reject"


def route_after_credit(state: ApplicationState) -> str:
    """Node 4 → Node 5 or END.
    Only approved credit decisions proceed to ART negotiation.
    """
    if state.get("credit_decision") == "approve":
        return "continue"
    return "reject"


def route_after_art(state: ApplicationState) -> str:
    """Node 5 → Node 6, or wait for HITL, or END.
    For loans > HITL threshold: graph was interrupted before this node ran
    and the RM decision was injected into state before resuming.
    If RM rejected → END. Otherwise proceed to e-NACH.
    """
    if state.get("hitl_required") and state.get("hitl_decision") is None:
        return "hitl"
    if state.get("hitl_decision") == "reject":
        return "reject"
    return "continue"
