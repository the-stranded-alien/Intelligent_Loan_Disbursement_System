from graph.state import ApplicationState
from services.event_publisher import event_publisher


async def run_credit_assessment(state: ApplicationState) -> ApplicationState:
    """
    Node: credit_assessment
    Responsibility: Pull credit bureau report (CIBIL/Experian), analyse credit score,
    existing liabilities, repayment history, compute final credit decision.
    """
    # TODO: Call credit bureau tool, render prompt with bureau data,
    #       parse JSON → credit_score, credit_decision, suggested_loan_amount
    updated_state = {**state, "current_stage": "credit_assessment"}
    event_publisher.publish(
        stream="loan:events",
        event_type="node.completed",
        payload={
            "application_id": state.get("application_id"),
            "stage": "credit_assessment",
            "stage_results": updated_state.get("stage_results", {}),
        },
    )
    return updated_state
