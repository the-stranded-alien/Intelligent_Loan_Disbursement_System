from fastapi import FastAPI

from config.settings import settings

app = FastAPI(
    title="Loan Agent Service",
    description="LangGraph pipeline service for the Intelligent Loan Disbursement System",
    version="0.1.0",
)


@app.get("/health", tags=["health"])
async def health_check():
    return {"status": "ok", "service": "agent-service"}
