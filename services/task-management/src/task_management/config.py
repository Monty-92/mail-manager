from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    service_name: str = "task-management"
    database_url: str = "postgresql+asyncpg://mailmanager:mailmanager_dev@postgres:5432/mailmanager"
    redis_url: str = "redis://redis:6379/0"
    host: str = "0.0.0.0"
    port: int = 8006

    model_config = {"env_prefix": "", "env_file": ".env"}


settings = Settings()
