from fastapi import APIRouter

router = APIRouter()


@router.post("/disburse/callback")
async def disbursement_callback():
    # TODO: Handle bank disbursement confirmation webhook
    pass


@router.post("/kyc/callback")
async def kyc_callback():
    # TODO: Handle external KYC provider webhook
    pass
