---
description: Add a new notification template and task (SMS, WhatsApp, or Email) for a pipeline event
argument-hint: "<event_name> <channel: sms|whatsapp|email>"
---

## Context

- Existing notification tasks: !`cat notification-service/worker/tasks.py 2>/dev/null | head -60 || echo "tasks.py not found"`
- Existing templates: !`find notification-service/templates -name "*.j2" 2>/dev/null || echo "No templates found"`
- Beat schedule: !`cat notification-service/worker/beat_schedule.py 2>/dev/null || echo "beat_schedule.py not found"`
- Event consumer: !`cat notification-service/consumers/event_consumer.py 2>/dev/null || echo "consumer not found"`
- Arguments: $ARGUMENTS

## Your task

Add a new notification for event **$ARGUMENTS**.

Parse `$ARGUMENTS`:
- First token = event name (e.g. `node.completed`, `hitl.requested`, `pipeline.completed`)
- Second token = channel (`sms`, `whatsapp`, `email`, or `all`)

If arguments are missing, ask the user:
1. Which event triggers this notification?
2. Who receives it (applicant, RM, ops team)?
3. Which channel(s): SMS, WhatsApp, Email?
4. Is it triggered by an event or a Celery Beat schedule?

### Steps

1. **Create the Jinja2 template(s)**

   For SMS/WhatsApp: `notification-service/templates/<channel>/<event_slug>.j2`
   ```
   Dear {{ applicant_name }},
   Your loan application ({{ application_id[:8] }}) — {{ message }}.
   Reply STOP to unsubscribe.
   ```

   For email: `notification-service/templates/email/<event_slug>.j2` (HTML with subject line)

2. **Create/update the handler** in `notification-service/handlers/<event_slug>_handler.py`:
   - Load appropriate template
   - Render with application context
   - Return rendered message + recipient details

3. **Add the Celery task** in `notification-service/worker/tasks.py`:
   ```python
   @app.task(name="send_<event_slug>_notification", bind=True, max_retries=3)
   def send_<event_slug>_notification(self, application_id: str, **kwargs):
       ...
   ```

4. **Wire the event consumer** in `notification-service/consumers/event_consumer.py`:
   - Add handling for the new event stream
   - Enqueue the new Celery task when the event arrives

5. **If scheduled** (Celery Beat): Add the schedule to `notification-service/worker/beat_schedule.py`

6. **Write a test** in `notification-service/tests/test_<event_slug>_notification.py`:
   - Mock Twilio/SendGrid clients
   - Assert template renders correctly
   - Assert task enqueues without error

7. **Show all files created/modified**.
