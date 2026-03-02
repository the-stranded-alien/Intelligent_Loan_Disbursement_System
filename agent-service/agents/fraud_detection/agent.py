from graph.state import ApplicationState


async def run_fraud_detection(state: ApplicationState) -> ApplicationState:
    """
    Node: fraud_detection
    Responsibility: Run velocity checks, device fingerprint analysis, cross-application
    duplicate detection, and ML fraud signals. Decide clear/flag/block.
    """
    # TODO: Run fraud tools, render prompt with signals,
    #       parse JSON → fraud_risk_score, fraud_signals, fraud_decision
    return {**state, "current_stage": "fraud_detection"}
