from graph.state import ApplicationState
from config.settings import settings


async def run_sanction_processing(state: ApplicationState) -> ApplicationState:
    """
    Node: sanction_processing
    Responsibility: Compute final sanctioned amount, terms, and interest rate.
    For loans > HITL_THRESHOLD (₹10L), set hitl_required=True and raise interrupt
    for RM review. Process RM decision on resume.
    """
    loan_amount = state.get("loan_amount", 0)
    hitl_required = loan_amount > settings.hitl_threshold

    # TODO: Render sanction prompt, call Claude to compute sanction terms,
    #       set hitl_required flag; on resume, process hitl_decision from state
    return {
        **state,
        "current_stage": "sanction_processing",
        "hitl_required": hitl_required,
    }
