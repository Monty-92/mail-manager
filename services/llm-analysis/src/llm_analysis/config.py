from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    service_name: str = "llm-analysis"
    database_url: str = "postgresql+asyncpg://mailmanager:mailmanager_dev@postgres:5432/mailmanager"
    redis_url: str = "redis://redis:6379/0"
    ollama_base_url: str = "http://ollama:11434"
    ollama_model: str = "llama3.1:8b"
    ollama_embed_model: str = "nomic-embed-text"
    host: str = "0.0.0.0"
    port: int = 8003

    model_config = {"env_prefix": "", "env_file": ".env"}


settings = Settings()
