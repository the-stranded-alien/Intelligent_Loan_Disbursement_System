import logging
from worker.celery_app import celery_app
from services.sendgrid_service import sendgrid_service
from services.twilio_service import twilio_service

logger = logging.getLogger(__name__)


@celery_app.task(name="notify.send_outreach", queue="notifications")
def notify_outreach(
    application_id: str,
    email: str,
    phone: str,
    full_name: str,
    subject: str,
    email_body: str,
    sms_text: str,
) -> dict:
    """Send outreach email + SMS for a stale application."""
    email_ok = False
    sms_ok = False

    first_name = full_name.split()[0] if full_name else full_name

    html_body = email_body.replace("\n", "<br>")

    if email:
        email_ok = sendgrid_service.send_email(
            to_email=email,
            to_name=full_name,
            subject=subject,
            html_content=html_body,
            text_content=email_body,
        )

    if phone:
        sms_ok = twilio_service.send_sms(to=phone, body=sms_text) is not None

    logger.info(
        "Outreach notifications for %s: email=%s sms=%s",
        application_id, email_ok, sms_ok,
    )
    return {"application_id": application_id, "email_sent": email_ok, "sms_sent": sms_ok}


@celery_app.task(name="notify.application_received", queue="notifications")
def notify_application_received(application_id: str, applicant_data: dict) -> bool:
    """Send confirmation SMS + email when a new loan application is received."""
    first_name = applicant_data.get("full_name", "Applicant").split()[0]
    email = applicant_data.get("email", "")
    phone = applicant_data.get("phone", "")
    loan_amount = applicant_data.get("loan_amount", 0)

    subject = "Your loan application has been received"
    body = (
        f"Hi {first_name},\n\n"
        f"We've received your loan application for ₹{int(loan_amount):,}. "
        f"Our AI pipeline is now processing your application.\n\n"
        f"You can track status at any time using your application ID: {application_id}\n\n"
        f"Best regards,\nLoanFlow Team"
    )
    sms = f"Hi {first_name}, your LoanFlow application ({application_id[:8]}…) is being processed. We'll update you shortly."

    if email:
        sendgrid_service.send_email(to_email=email, to_name=applicant_data.get("full_name", ""), subject=subject, html_content=body.replace("\n", "<br>"), text_content=body)
    if phone:
        twilio_service.send_sms(to=phone, body=sms)
    return True


@celery_app.task(name="notify.application_approved", queue="notifications")
def notify_application_approved(application_id: str, applicant_data: dict, sanction_terms: dict) -> bool:
    """Notify applicant of loan approval with sanctioned terms."""
    first_name = applicant_data.get("full_name", "Applicant").split()[0]
    email = applicant_data.get("email", "")
    phone = applicant_data.get("phone", "")
    rate = sanction_terms.get("interest_rate", "")
    tenure = sanction_terms.get("tenure_months", "")
    emi = sanction_terms.get("emi_amount", "")

    subject = "Congratulations — Your loan has been approved!"
    body = (
        f"Hi {first_name},\n\n"
        f"Great news! Your loan application has been approved.\n\n"
        f"Terms: {rate}% p.a. | {tenure} months | EMI ₹{int(emi):,}\n\n"
        f"e-NACH and e-Sign steps will be completed automatically. "
        f"Funds will be disbursed within 24 hours.\n\nLoanFlow Team"
    )
    sms = f"Hi {first_name}! Your LoanFlow loan is approved. EMI: ₹{int(emi):,}/mo. Disbursement in 24h."

    if email:
        sendgrid_service.send_email(to_email=email, to_name=applicant_data.get("full_name", ""), subject=subject, html_content=body.replace("\n", "<br>"), text_content=body)
    if phone:
        twilio_service.send_sms(to=phone, body=sms)
    return True


@celery_app.task(name="notify.application_rejected", queue="notifications")
def notify_application_rejected(application_id: str, applicant_data: dict, reason: str) -> bool:
    """Notify applicant of loan rejection with reason."""
    first_name = applicant_data.get("full_name", "Applicant").split()[0]
    email = applicant_data.get("email", "")
    phone = applicant_data.get("phone", "")

    subject = "Update on your loan application"
    body = (
        f"Hi {first_name},\n\n"
        f"We've reviewed your loan application and are unable to proceed at this time.\n\n"
        f"Reason: {reason}\n\n"
        f"You may re-apply after 90 days or contact us to discuss your options.\n\nLoanFlow Team"
    )
    sms = f"Hi {first_name}, your LoanFlow application couldn't be approved. Reason: {reason[:80]}. Contact us for help."

    if email:
        sendgrid_service.send_email(to_email=email, to_name=applicant_data.get("full_name", ""), subject=subject, html_content=body.replace("\n", "<br>"), text_content=body)
    if phone:
        twilio_service.send_sms(to=phone, body=sms)
    return True


@celery_app.task(name="notify.document_reminder", queue="notifications")
def notify_document_reminder(application_id: str, applicant_data: dict, missing_docs: list[str]) -> bool:
    """Remind applicant to upload missing documents."""
    first_name = applicant_data.get("full_name", "Applicant").split()[0]
    phone = applicant_data.get("phone", "")
    docs_str = ", ".join(missing_docs)
    sms = f"Hi {first_name}, please upload: {docs_str[:80]} to continue your LoanFlow application."
    if phone:
        twilio_service.send_sms(to=phone, body=sms)
    return True


@celery_app.task(name="notify.disbursement_initiated", queue="notifications")
def notify_disbursement_initiated(application_id: str, applicant_data: dict, disbursement_details: dict) -> bool:
    """Notify applicant that disbursement has been initiated."""
    first_name = applicant_data.get("full_name", "Applicant").split()[0]
    email = applicant_data.get("email", "")
    phone = applicant_data.get("phone", "")
    ref = disbursement_details.get("transaction_reference", "")

    subject = "Your loan disbursement is on its way!"
    body = f"Hi {first_name},\n\nYour loan has been disbursed. Ref: {ref}\nFunds should appear in your account within 2-4 hours.\n\nLoanFlow Team"
    sms = f"Hi {first_name}! LoanFlow disbursement initiated. Ref: {ref}. Funds arriving in 2-4h."

    if email:
        sendgrid_service.send_email(to_email=email, to_name=applicant_data.get("full_name", ""), subject=subject, html_content=body.replace("\n", "<br>"), text_content=body)
    if phone:
        twilio_service.send_sms(to=phone, body=sms)
    return True


@celery_app.task(name="notify.disbursement_success", queue="notifications")
def notify_disbursement_success(application_id: str, applicant_data: dict, transaction_id: str) -> bool:
    """Confirm successful loan disbursement to applicant."""
    first_name = applicant_data.get("full_name", "Applicant").split()[0]
    email = applicant_data.get("email", "")
    phone = applicant_data.get("phone", "")

    subject = "Loan disbursement confirmed"
    body = f"Hi {first_name},\n\nYour loan has been successfully disbursed. Transaction ID: {transaction_id}\n\nThank you for choosing LoanFlow!\n\nLoanFlow Team"
    sms = f"Hi {first_name}! ₹ credited to your account. Txn: {transaction_id[:12]}. Thank you — LoanFlow."

    if email:
        sendgrid_service.send_email(to_email=email, to_name=applicant_data.get("full_name", ""), subject=subject, html_content=body.replace("\n", "<br>"), text_content=body)
    if phone:
        twilio_service.send_sms(to=phone, body=sms)
    return True


@celery_app.task(name="notify.hitl_pending", queue="notifications")
def notify_hitl_pending(application_id: str, rm_data: dict) -> bool:
    """Notify RM that a loan application requires human review."""
    rm_email = rm_data.get("email", "")
    applicant_name = rm_data.get("applicant_name", "")
    loan_amount = rm_data.get("loan_amount", 0)

    subject = f"HITL Review Required — {applicant_name}"
    body = (
        f"A loan application requires your review.\n\n"
        f"Applicant: {applicant_name}\n"
        f"Amount: ₹{int(loan_amount):,}\n"
        f"Application ID: {application_id}\n\n"
        f"Please log in to the RM Dashboard to review and approve/reject."
    )
    if rm_email:
        sendgrid_service.send_email(to_email=rm_email, to_name="Relationship Manager", subject=subject, html_content=body.replace("\n", "<br>"), text_content=body)
    return True
