from fastapi import APIRouter

router = APIRouter()


@router.post("/")
async def create_application():
    # TODO: Accept loan application, publish to Redis Streams, return application_id
    pass


@router.get("/{application_id}")
async def get_application(application_id: str):
    # TODO: Fetch application status + pipeline stage
    pass


@router.get("/{application_id}/status")
async def get_application_status(application_id: str):
    # TODO: Return detailed pipeline status with each node result
    pass


@router.get("/")
async def list_applications():
    # TODO: List applications with filters (status, date range, RM)
    pass
