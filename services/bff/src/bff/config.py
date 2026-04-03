from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    service_name: str = "bff"
    database_url: str = "postgresql+asyncpg://mailmanager:mailmanager_dev@postgres:5432/mailmanager"
    redis_url: str = "redis://redis:6379/0"
    ingestion_url: str = "http://ingestion:8001"
    preprocessing_url: str = "http://preprocessing:8002"
    llm_analysis_url: str = "http://llm-analysis:8003"
    topic_tracking_url: str = "http://topic-tracking:8004"
    summary_generation_url: str = "http://summary-generation:8005"
    task_management_url: str = "http://task-management:8006"
    calendar_sync_url: str = "http://calendar-sync:8007"
    host: str = "0.0.0.0"
    port: int = 8000

    model_config = {"env_prefix": "", "env_file": ".env"}


settings = Settings()
