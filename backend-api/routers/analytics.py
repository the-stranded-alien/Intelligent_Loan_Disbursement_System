from fastapi import APIRouter

router = APIRouter()


@router.get("/overview")
async def get_overview():
    # TODO: Return aggregate metrics (total applications, approval rate, avg time)
    pass


@router.get("/pipeline")
async def get_pipeline_metrics():
    # TODO: Return per-node pass/fail rates and avg processing time
    pass


@router.get("/disbursements")
async def get_disbursement_metrics():
    # TODO: Return disbursement volume, amounts, success/failure rates
    pass
