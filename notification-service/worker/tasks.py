from worker.celery_app import celery_app


@celery_app.task(name="notify.application_received", queue="notifications")
def notify_application_received(application_id: str, applicant_data: dict) -> bool:
    """Send confirmation SMS + email when a new loan application is received."""
    # TODO: Render templates, call twilio_service.send_sms() and sendgrid_service.send_email()
    pass


@celery_app.task(name="notify.application_approved", queue="notifications")
def notify_application_approved(application_id: str, applicant_data: dict, sanction_terms: dict) -> bool:
    """Notify applicant of loan approval with sanctioned terms."""
    # TODO: Send WhatsApp + email with sanction letter details
    pass


@celery_app.task(name="notify.application_rejected", queue="notifications")
def notify_application_rejected(application_id: str, applicant_data: dict, reason: str) -> bool:
    """Notify applicant of loan rejection with reason."""
    # TODO: Send SMS + email with rejection reason and next steps
    pass


@celery_app.task(name="notify.document_reminder", queue="notifications")
def notify_document_reminder(application_id: str, applicant_data: dict, missing_docs: list[str]) -> bool:
    """Remind applicant to upload missing documents."""
    # TODO: Send SMS with list of missing documents and upload link
    pass


@celery_app.task(name="notify.disbursement_initiated", queue="notifications")
def notify_disbursement_initiated(application_id: str, applicant_data: dict, disbursement_details: dict) -> bool:
    """Notify applicant that disbursement has been initiated."""
    # TODO: Send WhatsApp + email with transaction reference and expected credit time
    pass


@celery_app.task(name="notify.disbursement_success", queue="notifications")
def notify_disbursement_success(application_id: str, applicant_data: dict, transaction_id: str) -> bool:
    """Confirm successful loan disbursement to applicant."""
    # TODO: Send confirmation SMS + email with final loan account details
    pass


@celery_app.task(name="notify.hitl_pending", queue="notifications")
def notify_hitl_pending(application_id: str, rm_data: dict) -> bool:
    """Notify RM that a loan application requires human review."""
    # TODO: Send email/Slack notification to assigned RM with review link
    pass
