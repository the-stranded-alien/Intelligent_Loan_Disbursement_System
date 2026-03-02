from graph.state import ApplicationState


async def run_lead_qualification(state: ApplicationState) -> ApplicationState:
    """
    Node: lead_qualification
    Responsibility: Evaluate eligibility criteria (age, income, loan amount limits),
    query RAG for relevant policy, decide qualified/rejected.
    """
    # TODO: RAG query for eligibility policy, render prompt, call Claude,
    #       parse JSON → qualification_result, qualification_notes
    return {**state, "current_stage": "lead_qualification"}
