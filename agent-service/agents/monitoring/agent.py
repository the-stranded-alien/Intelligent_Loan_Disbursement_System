"""
Applications Monitoring Agent

Scans all open applications and flags any that have had no update within
configurable time thresholds. Flagged applications are published to the
outreach.required Redis stream for the Outreach Agent to process.
"""

import logging
from datetime import datetime, timezone, timedelta

from config.settings import settings
from services.event_publisher import event_publisher
from db.session import SessionLocal, Application, AuditLog
from sqlalchemy import func

logger = logging.getLogger(__name__)

# Staleness thresholds per status (in hours — fractions supported for demo)
STALE_THRESHOLDS: dict[str, float] = {
    "pending":        0.05,  # ~3 min — submitted but pipeline never started
    "processing":     0.05,  # ~3 min — pipeline stuck mid-run
    "pending_review": 0.05,  # ~3 min — HITL requested but RM hasn't acted
    "info_requested": 0.05,  # ~3 min — applicant hasn't completed assessment chat
}

# Max outreach attempts before we stop (checked via audit_log count)
MAX_OUTREACH_ATTEMPTS = 4


def run_monitoring_scan() -> list[dict]:
    """
    Scan all open applications for staleness.
    Returns a list of stale application dicts — each will trigger an outreach.
    Publishes outreach.required events for applications that qualify.
    """
    db = SessionLocal()
    stale_apps = []

    try:
        now = datetime.now(timezone.utc)
        now_naive = now.replace(tzinfo=None)   # DB stores naive UTC datetimes

        for status, hours in STALE_THRESHOLDS.items():
            cutoff = now_naive - timedelta(hours=hours)

            apps = (
                db.query(Application)
                .filter(
                    Application.status == status,
                    Application.updated_at < cutoff,
                )
                .all()
            )

            for app in apps:
                # Check how many outreach events already sent for this application
                outreach_count = (
                    db.query(func.count(AuditLog.id))
                    .filter(
                        AuditLog.application_id == app.id,
                        AuditLog.event_type == "outreach.sent",
                    )
                    .scalar()
                    or 0
                )

                if outreach_count >= MAX_OUTREACH_ATTEMPTS:
                    logger.info(
                        "Skipping %s — already %d outreach attempts sent",
                        app.id, outreach_count,
                    )
                    continue

                updated_at = app.updated_at
                if updated_at.tzinfo is None:
                    updated_at = updated_at.replace(tzinfo=timezone.utc)
                hours_stale = round((now - updated_at).total_seconds() / 3600, 1)

                stale_info = {
                    "application_id": app.id,
                    "full_name": app.full_name,
                    "email": app.email,
                    "phone": app.phone,
                    "loan_amount": app.loan_amount,
                    "loan_purpose": app.loan_purpose or "",
                    "status": app.status,
                    "current_stage": app.current_stage or "",
                    "hours_stale": hours_stale,
                    "outreach_attempt": outreach_count + 1,
                }

                stale_apps.append(stale_info)

                event_publisher.publish(
                    stream="loan:events",
                    event_type="outreach.required",
                    payload=stale_info,
                )

                # Directly enqueue the outreach Celery task (same worker process)
                from worker.tasks import run_outreach  # noqa: PLC0415
                run_outreach.delay(stale_info)

                logger.info(
                    "Flagged stale application %s (status=%s, stale=%.1fh, attempt=%d)",
                    app.id, status, hours_stale, outreach_count + 1,
                )

    except Exception as e:
        logger.error("Monitoring scan failed: %s", e)
    finally:
        db.close()

    logger.info("Monitoring scan complete — %d stale applications found", len(stale_apps))
    return stale_apps
