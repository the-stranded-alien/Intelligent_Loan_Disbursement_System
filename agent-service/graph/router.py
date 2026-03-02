from graph.state import ApplicationState


def route_after_qualification(state: ApplicationState) -> str:
    """Route after lead_qualification: continue to identity verification or reject."""
    # TODO: return "continue" if state["qualification_result"] == "qualified" else "reject"
    return "continue"


def route_after_fraud(state: ApplicationState) -> str:
    """Route after fraud_detection: continue to compliance or block the application."""
    # TODO: return "block" if state["fraud_decision"] == "block" else "continue"
    return "continue"


def route_after_sanction(state: ApplicationState) -> str:
    """Route after sanction_processing: disburse, await HITL interrupt, or reject."""
    # TODO:
    #   if state["hitl_required"] and state["hitl_decision"] is None: return "hitl"
    #   if state["hitl_decision"] == "approve" or not state["hitl_required"]: return "disburse"
    #   return "reject"
    return "disburse"
