from graph.state import ApplicationState
from services.event_publisher import event_publisher


async def run_identity_verification(state: ApplicationState) -> ApplicationState:
    """
    Node: identity_verification
    Responsibility: Verify PAN, Aadhaar via external KYC provider,
    validate document authenticity via Google Document AI OCR.
    """
    # TODO: Call KYC provider API, call OCR service, render prompt,
    #       parse JSON → identity_verified, kyc_status
    updated_state = {**state, "current_stage": "identity_verification"}
    event_publisher.publish(
        stream="loan:events",
        event_type="node.completed",
        payload={
            "application_id": state.get("application_id"),
            "stage": "identity_verification",
            "stage_results": updated_state.get("stage_results", {}),
        },
    )
    return updated_state
