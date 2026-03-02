from celery.schedules import crontab
from worker.celery_app import celery_app

celery_app.conf.beat_schedule = {
    # Check for applications with missing documents every 4 hours (8am–8pm IST)
    "document-reminder-schedule": {
        "task": "notify.document_reminder_batch",
        "schedule": crontab(minute=0, hour="4,8,12,16"),  # UTC → IST +5:30
        "args": [],
    },
    # Remind RMs about applications pending review for > 2 hours
    "rm-followup-schedule": {
        "task": "notify.rm_followup_batch",
        "schedule": crontab(minute=30, hour="*/2"),
        "args": [],
    },
    # Nudge applicants who haven't e-signed sanction letter within 24h
    "sanction-nudge-schedule": {
        "task": "notify.sanction_nudge_batch",
        "schedule": crontab(minute=0, hour="3"),  # Daily at 8:30am IST
        "args": [],
    },
}
