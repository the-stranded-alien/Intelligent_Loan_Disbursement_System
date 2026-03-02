from fastapi import APIRouter

router = APIRouter()


@router.post("/{application_id}/upload")
async def upload_document(application_id: str):
    # TODO: Accept document upload, store, trigger OCR via agent-service
    pass


@router.get("/{application_id}")
async def list_documents(application_id: str):
    # TODO: List documents for an application with verification status
    pass


@router.delete("/{document_id}")
async def delete_document(document_id: str):
    # TODO: Soft-delete a document
    pass
