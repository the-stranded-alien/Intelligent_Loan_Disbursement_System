from graph.state import ApplicationState
from services.event_publisher import event_publisher


async def run_fraud_detection(state: ApplicationState) -> ApplicationState:
    """
    Node: fraud_detection
    Responsibility: Run velocity checks, device fingerprint analysis, cross-application
    duplicate detection, and ML fraud signals. Decide clear/flag/block.
    """
    # TODO: Run fraud tools, render prompt with signals,
    #       parse JSON → fraud_risk_score, fraud_signals, fraud_decision
    updated_state = {**state, "current_stage": "fraud_detection"}
    event_publisher.publish(
        stream="loan:events",
        event_type="node.completed",
        payload={
            "application_id": state.get("application_id"),
            "stage": "fraud_detection",
            "stage_results": updated_state.get("stage_results", {}),
        },
    )
    return updated_state
