from graph.state import ApplicationState
from services.event_publisher import event_publisher


async def run_disbursement(state: ApplicationState) -> ApplicationState:
    """
    Node: disbursement
    Responsibility: Initiate bank transfer via payment rail, confirm transaction,
    publish disbursement event. Retry schedule: immediate → 1h → 4h → 24h.
    """
    # TODO: Call disbursement tool, handle success/failure,
    #       set disbursement_status, disbursement_reference
    updated_state = {
        **state,
        "current_stage": "disbursement",
        "disbursement_status": "pending",
        "disbursement_attempts": state.get("disbursement_attempts", 0) + 1,
    }
    event_publisher.publish(
        stream="loan:events",
        event_type="node.completed",
        payload={
            "application_id": state.get("application_id"),
            "stage": "disbursement",
            "stage_results": updated_state.get("stage_results", {}),
        },
    )
    return updated_state
