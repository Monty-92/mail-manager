"""Pydantic models for the LLM analysis service."""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class EmailCategory(StrEnum):
    PERSONAL = "personal"
    WORK = "work"
    TRANSACTIONAL = "transactional"
    NEWSLETTER = "newsletter"
    MARKETING = "marketing"
    NOTIFICATION = "notification"
    SPAM = "spam"
    OTHER = "other"


class UrgencyLevel(StrEnum):
    CRITICAL = "critical"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"
    NONE = "none"


class Sentiment(StrEnum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    MIXED = "mixed"


class ActionItem(BaseModel):
    """A single action item extracted from an email."""

    description: str
    assignee: str | None = None
    due_hint: str | None = None


class PreprocessedEvent(BaseModel):
    """Inbound event from mailmanager.email.preprocessed Redis channel."""

    email_id: str
    status: str


class EmailForAnalysis(BaseModel):
    """Email record fetched from the database for LLM analysis."""

    id: str
    provider: str
    sender: str
    recipients: list[str] = Field(default_factory=list)
    subject: str
    markdown_body: str
    received_at: datetime


class AnalysisResult(BaseModel):
    """Full analysis result for a single email."""

    email_id: str
    category: EmailCategory = EmailCategory.OTHER
    urgency: UrgencyLevel = UrgencyLevel.NORMAL
    summary: str = ""
    action_items: list[ActionItem] = Field(default_factory=list)
    key_topics: list[str] = Field(default_factory=list)
    sentiment: Sentiment = Sentiment.NEUTRAL
    is_junk: bool = False
    confidence: float = 0.0
    model_used: str = ""
    error: str | None = None


class StoredAnalysis(BaseModel):
    """Analysis record as stored in the database."""

    id: str
    email_id: str
    category: EmailCategory
    urgency: UrgencyLevel
    summary: str
    action_items: list[ActionItem]
    key_topics: list[str]
    sentiment: Sentiment
    is_junk: bool
    confidence: float
    model_used: str
    created_at: datetime
    updated_at: datetime
