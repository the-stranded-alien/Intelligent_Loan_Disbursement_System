import logging
from config.settings import settings

logger = logging.getLogger(__name__)


class TwilioService:
    """Twilio SMS and WhatsApp notification service."""

    def __init__(self):
        self._client = None

    def _get_client(self):
        if self._client is None:
            if not settings.twilio_account_sid or not settings.twilio_auth_token:
                return None
            from twilio.rest import Client
            self._client = Client(settings.twilio_account_sid, settings.twilio_auth_token)
        return self._client

    def send_sms(self, to: str, body: str) -> str | None:
        """Send an SMS and return the Twilio message SID, or None on failure."""
        client = self._get_client()
        if not client:
            logger.warning("Twilio not configured — skipping SMS to %s", to)
            return None
        try:
            message = client.messages.create(
                to=to,
                from_=settings.twilio_phone_number,
                body=body,
            )
            logger.info("SMS sent to %s: SID %s", to, message.sid)
            return message.sid
        except Exception as e:
            logger.error("Twilio SMS error for %s: %s", to, e)
            return None

    def send_whatsapp(self, to: str, body: str) -> str | None:
        """Send a WhatsApp message and return the Twilio message SID."""
        client = self._get_client()
        if not client:
            logger.warning("Twilio not configured — skipping WhatsApp to %s", to)
            return None
        try:
            wa_from = settings.twilio_whatsapp_number
            wa_to = f"whatsapp:{to}" if not to.startswith("whatsapp:") else to
            message = client.messages.create(to=wa_to, from_=wa_from, body=body)
            logger.info("WhatsApp sent to %s: SID %s", to, message.sid)
            return message.sid
        except Exception as e:
            logger.error("Twilio WhatsApp error for %s: %s", to, e)
            return None


twilio_service = TwilioService()
