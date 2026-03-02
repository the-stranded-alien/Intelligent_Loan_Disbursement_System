from config.settings import settings


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
        # TODO: Build SendGrid Mail object, call sendgrid.SendGridAPIClient().send()
        pass

    def send_template_email(
        self,
        to_email: str,
        to_name: str,
        template_id: str,
        dynamic_data: dict,
    ) -> bool:
        """Send email using a SendGrid dynamic template."""
        # TODO: Use SendGrid dynamic templates for rich HTML emails
        pass


sendgrid_service = SendGridService()
