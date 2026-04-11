from fastapi import FastAPI
from pydantic import BaseModel

from config.settings import settings

app = FastAPI(
    title="Loan Notification Service",
    description="Event-driven notification service (SMS, WhatsApp, Email) for the Loan Disbursement System",
    version="0.1.0",
)


@app.get("/health", tags=["health"])
async def health_check():
    return {"status": "ok", "service": "notification-service"}


class OutreachRequest(BaseModel):
    application_id: str
    email: str = ""
    phone: str = ""
    full_name: str = ""
    subject: str
    email_body: str
    sms_text: str


@app.post("/internal/send-outreach", tags=["internal"])
async def send_outreach(req: OutreachRequest):
    """Called by agent-service outreach agent to dispatch email + SMS."""
    from worker.tasks import notify_outreach
    notify_outreach.delay(
        application_id=req.application_id,
        email=req.email,
        phone=req.phone,
        full_name=req.full_name,
        subject=req.subject,
        email_body=req.email_body,
        sms_text=req.sms_text,
    )
    return {"queued": True, "application_id": req.application_id}
