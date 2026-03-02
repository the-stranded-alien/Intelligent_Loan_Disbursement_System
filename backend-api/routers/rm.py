from fastapi import APIRouter

router = APIRouter()


@router.get("/queue")
async def get_rm_queue():
    # TODO: Return pending HITL reviews for the RM dashboard
    pass


@router.post("/{application_id}/review")
async def submit_review(application_id: str):
    # TODO: Accept RM approve/reject decision, resume LangGraph pipeline
    pass


@router.get("/{application_id}/context")
async def get_review_context(application_id: str):
    # TODO: Return full AI analysis context for RM review screen
    pass
