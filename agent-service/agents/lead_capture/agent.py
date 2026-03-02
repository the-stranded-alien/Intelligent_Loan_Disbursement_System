from graph.state import ApplicationState


async def run_lead_capture(state: ApplicationState) -> ApplicationState:
    """
    Node: lead_capture
    Responsibility: Validate and normalize incoming lead data, assign lead source,
    compute initial lead score, and prepare state for qualification.
    """
    # TODO: Render lead_capture.j2 prompt, call Claude, parse JSON response,
    #       update state with lead_score and lead_source
    return {**state, "current_stage": "lead_capture"}
