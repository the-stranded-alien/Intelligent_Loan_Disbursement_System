from config.settings import settings


class TwilioService:
    """Twilio SMS and WhatsApp notification service."""

    def __init__(self):
        self._client = None

    def _get_client(self):
        # TODO: Lazy-init Twilio Client with account_sid and auth_token
        pass

    def send_sms(self, to: str, body: str) -> str:
        """Send an SMS and return the Twilio message SID."""
        # TODO: self._get_client().messages.create(to=to, from_=settings.twilio_phone_number, body=body)
        pass

    def send_whatsapp(self, to: str, body: str) -> str:
        """Send a WhatsApp message and return the Twilio message SID."""
        # TODO: Send via Twilio WhatsApp sandbox / business account
        pass


twilio_service = TwilioService()
