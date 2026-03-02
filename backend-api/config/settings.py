from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database
    database_url: str = "postgresql://loan_user:changeme@localhost:5432/loan_db"

    # Redis
    redis_streams_url: str = "redis://localhost:6379/0"
    redis_celery_url: str = "redis://localhost:6379/1"
    redis_cache_url: str = "redis://localhost:6379/2"

    # Auth
    secret_key: str = "dev-secret-key"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    # CORS
    allowed_origins: list[str] = ["http://localhost:3000"]

    # Services
    agent_service_url: str = "http://localhost:8001"

    # Storage
    storage_backend: str = "local"
    local_storage_path: str = "/app/uploads"
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_s3_bucket: str = ""
    aws_region: str = "ap-south-1"

    # App
    environment: str = "development"
    log_level: str = "INFO"
    hitl_threshold: int = 1_000_000


settings = Settings()
