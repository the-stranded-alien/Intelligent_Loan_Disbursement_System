from graph.state import ApplicationState


async def run_identity_verification(state: ApplicationState) -> ApplicationState:
    """
    Node: identity_verification
    Responsibility: Verify PAN, Aadhaar via external KYC provider,
    validate document authenticity via Google Document AI OCR.
    """
    # TODO: Call KYC provider API, call OCR service, render prompt,
    #       parse JSON → identity_verified, kyc_status
    return {**state, "current_stage": "identity_verification"}
