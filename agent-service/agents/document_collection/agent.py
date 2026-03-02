from graph.state import ApplicationState


async def run_document_collection(state: ApplicationState) -> ApplicationState:
    """
    Node: document_collection
    Responsibility: Determine required documents based on loan type and applicant profile,
    verify uploaded documents via OCR, and flag missing/invalid documents.
    """
    # TODO: Determine doc checklist, verify each document OCR result,
    #       update documents_verified, required_documents
    return {**state, "current_stage": "document_collection"}
