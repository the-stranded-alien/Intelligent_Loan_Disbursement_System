from graph.state import ApplicationState


def route_after_qualification(state: ApplicationState) -> str:
    """Route after lead_qualification: continue to identity verification or reject."""
    result = state.get("qualification_result")
    if result == "qualified":
        return "continue"
    return "reject"


def route_after_fraud(state: ApplicationState) -> str:
    """Route after fraud_detection: continue to compliance or block the application."""
    # TODO: return "block" if state["fraud_decision"] == "block" else "continue"
    return "continue"


def route_after_sanction(state: ApplicationState) -> str:
    """Route after sanction_processing: disburse, await HITL interrupt, or reject."""
    if state.get("hitl_required") and state.get("hitl_decision") is None:
        return "hitl"
    if state.get("hitl_decision") == "reject":
        return "reject"
    return "disburse"
