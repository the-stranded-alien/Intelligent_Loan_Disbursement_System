from graph.state import ApplicationState


async def run_disbursement(state: ApplicationState) -> ApplicationState:
    """
    Node: disbursement
    Responsibility: Initiate bank transfer via payment rail, confirm transaction,
    publish disbursement event. Retry schedule: immediate → 1h → 4h → 24h.
    """
    # TODO: Call disbursement tool, handle success/failure,
    #       set disbursement_status, disbursement_reference
    return {
        **state,
        "current_stage": "disbursement",
        "disbursement_status": "pending",
        "disbursement_attempts": state.get("disbursement_attempts", 0) + 1,
    }
