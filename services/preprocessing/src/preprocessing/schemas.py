from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel


class PreprocessingStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class EmailEvent(BaseModel):
    """Inbound event from mailmanager.email.new Redis channel."""

    id: str
    provider: str
    external_id: str
    sender: str
    subject: str
    received_at: datetime


class EmailRecord(BaseModel):
    """Email as read from the database for preprocessing."""

    id: str
    provider: str
    external_id: str
    sender: str
    subject: str
    markdown_body: str
    received_at: datetime


class EmbeddingResult(BaseModel):
    """Result from Ollama embedding generation."""

    embedding: list[float]
    model: str
    token_count: int = 0


class PreprocessResult(BaseModel):
    """Result of preprocessing a single email."""

    email_id: str
    cleaned_text: str
    embedding_dim: int
    status: PreprocessingStatus
    error: str | None = None
