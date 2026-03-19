from graph.state import ApplicationState
from services.event_publisher import event_publisher


async def run_lead_qualification(state: ApplicationState) -> ApplicationState:
    """
    Node: lead_qualification
    Responsibility: Evaluate eligibility criteria (age, income, loan amount limits),
    query RAG for relevant policy, decide qualified/rejected.
    """
    # TODO: RAG query for eligibility policy, render prompt, call Claude,
    #       parse JSON → qualification_result, qualification_notes
    updated_state = {**state, "current_stage": "lead_qualification"}
    event_publisher.publish(
        stream="loan:events",
        event_type="node.completed",
        payload={
            "application_id": state.get("application_id"),
            "stage": "lead_qualification",
            "stage_results": updated_state.get("stage_results", {}),
        },
    )
    return updated_state
