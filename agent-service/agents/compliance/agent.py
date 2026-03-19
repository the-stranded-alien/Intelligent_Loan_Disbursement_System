from graph.state import ApplicationState
from services.event_publisher import event_publisher


async def run_compliance(state: ApplicationState) -> ApplicationState:
    """
    Node: compliance
    Responsibility: Run AML (Anti-Money Laundering) checks, PEP (Politically Exposed
    Person) screening, sanctions list lookup, and RBI regulatory compliance checks.
    """
    # TODO: Run compliance tools, query RAG for AML/RBI policy,
    #       render prompt, parse JSON → compliance_checks, compliance_decision
    updated_state = {**state, "current_stage": "compliance"}
    event_publisher.publish(
        stream="loan:events",
        event_type="node.completed",
        payload={
            "application_id": state.get("application_id"),
            "stage": "compliance",
            "stage_results": updated_state.get("stage_results", {}),
        },
    )
    return updated_state
