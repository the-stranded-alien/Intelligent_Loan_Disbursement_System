from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Redis
    redis_streams_url: str = "redis://localhost:6379/0"
    redis_celery_url: str = "redis://localhost:6379/1"

    # Twilio
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_phone_number: str = ""
    twilio_whatsapp_number: str = "whatsapp:+14155238886"

    # SendGrid
    sendgrid_api_key: str = ""
    sendgrid_from_email: str = "noreply@loanservice.example.com"
    sendgrid_from_name: str = "Loan Disbursement System"

    # App
    environment: str = "development"
    log_level: str = "INFO"


settings = Settings()
