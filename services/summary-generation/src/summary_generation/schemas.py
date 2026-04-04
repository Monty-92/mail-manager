"""Pydantic models for the summary generation service."""

from datetime import date, datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class SummaryType(StrEnum):
    MORNING = "morning"
    EVENING = "evening"


class EmailDigestEntry(BaseModel):
    """A single email's contribution to a digest summary."""

    email_id: str
    sender: str
    subject: str
    category: str = "other"
    urgency: str = "normal"
    summary: str = ""
    action_items: list[str] = Field(default_factory=list)
    key_topics: list[str] = Field(default_factory=list)


class ThreadSummaryRequest(BaseModel):
    """Request to summarize an email thread."""

    thread_id: str


class DailySummaryRequest(BaseModel):
    """Request to generate a daily summary."""

    date: date
    summary_type: SummaryType


class Summary(BaseModel):
    """A summary entity as stored in the database."""

    id: str
    summary_type: SummaryType
    date: date
    markdown_body: str
    embedding: list[float] | None = None
    diff_hash: str | None = None
    topic_ids: list[str] = Field(default_factory=list)
    created_at: datetime | None = None


class SummaryListItem(BaseModel):
    """Lightweight summary info for list views (no body or embedding)."""

    id: str
    summary_type: SummaryType
    date: date
    diff_hash: str | None = None
    created_at: datetime | None = None


class SummaryResult(BaseModel):
    """Result of a summary generation operation."""

    summary_id: str | None = None
    summary_type: SummaryType
    date: date
    email_count: int = 0
    topic_count: int = 0
    is_regenerated: bool = False
    error: str | None = None


class TopicsAssignedEvent(BaseModel):
    """Inbound event from mailmanager.email.topics_assigned Redis channel."""

    email_id: str
    topic_count: int
