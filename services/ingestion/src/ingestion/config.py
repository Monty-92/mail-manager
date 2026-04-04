from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    service_name: str = "ingestion"
    database_url: str = "postgresql+asyncpg://mailmanager:mailmanager_dev@postgres:5432/mailmanager"
    redis_url: str = "redis://redis:6379/0"
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:3000/auth/callback"
    ms_client_id: str = ""
    ms_client_secret: str = ""
    ms_tenant_id: str = "common"
    ms_redirect_uri: str = "http://localhost:3000/auth/callback"
    frontend_url: str = "http://localhost:3000"
    host: str = "0.0.0.0"
    port: int = 8001

    model_config = {"env_prefix": "", "env_file": ".env"}


settings = Settings()
