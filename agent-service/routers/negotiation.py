from fastapi import APIRouter
from agents.negotiation.agent import run_negotiation_analysis

router = APIRouter()


@router.post("/analyse")
async def analyse(application_data: dict):
    """Generate offer recommendation advice for the RM."""
    return await run_negotiation_analysis(application_data)
