import logging
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Content, To
from config.settings import settings

logger = logging.getLogger(__name__)


class SendGridService:
    """SendGrid email notification service."""

    def send_email(
        self,
        to_email: str,
        to_name: str,
        subject: str,
        html_content: str,
        text_content: str = "",
    ) -> bool:
        """Send a transactional email via SendGrid. Returns True on success."""
        if not settings.sendgrid_api_key:
            logger.warning("SENDGRID_API_KEY not set — skipping email to %s", to_email)
            return False
        try:
            message = Mail(
                from_email=(settings.sendgrid_from_email, settings.sendgrid_from_name),
                to_emails=To(to_email, to_name),
                subject=subject,
            )
            if html_content:
                message.content = [Content("text/html", html_content)]
            elif text_content:
                message.content = [Content("text/plain", text_content)]

            sg = SendGridAPIClient(settings.sendgrid_api_key)
            response = sg.send(message)
            logger.info("Email sent to %s: status %s", to_email, response.status_code)
            return response.status_code in (200, 202)
        except Exception as e:
            logger.error("SendGrid error for %s: %s", to_email, e)
            return False

    def send_template_email(
        self,
        to_email: str,
        to_name: str,
        template_id: str,
        dynamic_data: dict,
    ) -> bool:
        """Send email using a SendGrid dynamic template."""
        if not settings.sendgrid_api_key:
            logger.warning("SENDGRID_API_KEY not set — skipping template email to %s", to_email)
            return False
        try:
            message = Mail(
                from_email=(settings.sendgrid_from_email, settings.sendgrid_from_name),
                to_emails=To(to_email, to_name),
            )
            message.template_id = template_id
            message.dynamic_template_data = dynamic_data
            sg = SendGridAPIClient(settings.sendgrid_api_key)
            response = sg.send(message)
            return response.status_code in (200, 202)
        except Exception as e:
            logger.error("SendGrid template email error for %s: %s", to_email, e)
            return False


sendgrid_service = SendGridService()
