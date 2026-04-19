from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Anthropic
    anthropic_api_key: str = ""

    # OpenAI — used only by seed_embeddings.py for generating pgvector embeddings
    openai_api_key: str = ""

    # Database
    database_url: str = "postgresql://loan_user:changeme@localhost:5432/loan_db"

    # Redis
    redis_streams_url: str = "redis://localhost:6379/0"
    redis_celery_url: str = "redis://localhost:6379/1"
    redis_cache_url: str = "redis://localhost:6379/2"

    # Services
    backend_api_url: str = "http://localhost:8000"
    notification_service_url: str = "http://localhost:8002"

    # RAG
    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 1536
    rag_collection_name: str = "compliance_policies"

    # Pipeline
    hitl_threshold: int = 200_000
    disbursement_max_retries: int = 4

    # LangSmith tracing (optional)
    langchain_tracing_v2: str = "false"
    langchain_api_key: str = ""
    langchain_project: str = "loan-disbursement-system"

    # App
    environment: str = "development"
    log_level: str = "INFO"


settings = Settings()
