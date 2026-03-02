from fastapi import FastAPI

from config.settings import settings

app = FastAPI(
    title="Loan Notification Service",
    description="Event-driven notification service (SMS, WhatsApp, Email) for the Loan Disbursement System",
    version="0.1.0",
)


@app.get("/health", tags=["health"])
async def health_check():
    return {"status": "ok", "service": "notification-service"}
