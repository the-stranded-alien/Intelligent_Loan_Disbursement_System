from graph.state import ApplicationState
from services.event_publisher import event_publisher


async def run_document_collection(state: ApplicationState) -> ApplicationState:
    """
    Node: document_collection
    Responsibility: Determine required documents based on loan type and applicant profile,
    verify uploaded documents via OCR, and flag missing/invalid documents.
    """
    # TODO: Determine doc checklist, verify each document OCR result,
    #       update documents_verified, required_documents
    updated_state = {**state, "current_stage": "document_collection"}
    event_publisher.publish(
        stream="loan:events",
        event_type="node.completed",
        payload={
            "application_id": state.get("application_id"),
            "stage": "document_collection",
            "stage_results": updated_state.get("stage_results", {}),
        },
    )
    return updated_state
