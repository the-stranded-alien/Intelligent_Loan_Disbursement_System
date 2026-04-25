"""
Outreach Agent

Given a stale application payload (from the Monitoring Agent), generates
a personalised follow-up message via Claude, dispatches it through the
notification-service, and writes an `outreach.sent` audit log entry.
"""

import logging
from datetime import datetime, timezone
from pathlib import Path

import anthropic
import httpx
from jinja2 import Environment, FileSystemLoader

from config.settings import settings
from services.event_publisher import event_publisher
from services.json_parser import parse_llm_json

logger = logging.getLogger(__name__)

_PROMPTS_DIR = Path(__file__).parent.parent.parent / "config" / "prompts"


def _format_inr(value) -> str:
    """Indian number format: 1,00,000"""
    s = str(int(value))
    if len(s) <= 3:
        return s
    result = s[-3:]
    s = s[:-3]
    while len(s) > 2:
        result = s[-2:] + "," + result
        s = s[:-2]
    if s:
        result = s + "," + result
    return result


def _render_prompt(payload: dict) -> str:
    env = Environment(loader=FileSystemLoader(str(_PROMPTS_DIR)))
    env.filters["format_inr"] = _format_inr
    template = env.get_template("outreach.j2")
    return template.render(**payload)


async def run_outreach(payload: dict) -> dict:
    """
    Generate and dispatch a personalised follow-up for a stale application.

    payload keys: application_id, full_name, email, phone, loan_amount,
                  loan_purpose, status, current_stage, hours_stale, outreach_attempt
    """
    application_id = payload["application_id"]
    attempt = payload.get("outreach_attempt", 1)

    logger.info("Outreach agent: %s (attempt %d)", application_id, attempt)

    # 1. Render Jinja2 prompt and call Claude
    prompt = _render_prompt(payload)
    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key or None)

    response = await client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=512,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = response.content[0].text.strip()
    message_data = parse_llm_json(raw)

    subject = message_data.get("subject", "Update on your loan application")
    email_body = message_data.get("email_body", "")
    sms_text = message_data.get("sms_text", "")
    urgency = message_data.get("urgency", "medium")
    followup_days = int(message_data.get("suggested_followup_days", 2))

    logger.info("Message generated: subject=%r urgency=%s", subject, urgency)

    # 2. Dispatch via notification-service
    try:
        async with httpx.AsyncClient(timeout=15.0) as http:
            resp = await http.post(
                f"{settings.notification_service_url}/internal/send-outreach",
                json={
                    "application_id": application_id,
                    "email": payload.get("email", ""),
                    "phone": payload.get("phone", ""),
                    "full_name": payload.get("full_name", ""),
                    "subject": subject,
                    "email_body": email_body,
                    "sms_text": sms_text,
                },
            )
            resp.raise_for_status()
    except Exception as e:
        logger.warning("Notification dispatch failed for %s: %s", application_id, e)

    # 3. Write outreach.sent to audit_log via agent-service DB session
    try:
        from db.session import SessionLocal, AuditLog  # noqa: PLC0415
        db = SessionLocal()
        try:
            db.add(AuditLog(
                application_id=application_id,
                event_type="outreach.sent",
                actor="outreach-agent",
                payload={
                    "attempt": attempt,
                    "urgency": urgency,
                    "subject": subject,
                    "sms_preview": sms_text[:60] if sms_text else "",
                    "followup_days": followup_days,
                },
                created_at=datetime.now(timezone.utc),
            ))
            db.commit()
        finally:
            db.close()
    except Exception as e:
        logger.error("Failed to write outreach.sent audit log for %s: %s", application_id, e)

    # 4. Publish event so backend-api can broadcast to connected WS clients
    event_publisher.publish(
        stream="loan:events",
        event_type="outreach.sent",
        payload={
            "application_id": application_id,
            "attempt": attempt,
            "urgency": urgency,
            "subject": subject,
        },
    )

    return {
        "application_id": application_id,
        "subject": subject,
        "urgency": urgency,
        "followup_days": followup_days,
    }
