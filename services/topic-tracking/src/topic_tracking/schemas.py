"""Pydantic models for the topic tracking service."""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class AnalyzedEvent(BaseModel):
    """Inbound event from mailmanager.email.analyzed Redis channel."""

    email_id: str
    category: str
    urgency: str


class TopicSnapshot(BaseModel):
    """A point-in-time snapshot of a topic's state."""

    date: str
    email_count: int
    sample_subjects: list[str] = Field(default_factory=list)


class Topic(BaseModel):
    """A topic entity as stored in the database."""

    id: str
    name: str
    embedding: list[float] | None = None
    snapshots: list[TopicSnapshot] = Field(default_factory=list)
    email_count: int = 0
    created_at: datetime | None = None
    updated_at: datetime | None = None


class TopicSummary(BaseModel):
    """Lightweight topic info for list views (no embedding)."""

    id: str
    name: str
    email_count: int = 0
    created_at: datetime | None = None
    updated_at: datetime | None = None


class TopicMatch(BaseModel):
    """Result of matching a topic name/embedding to existing topics."""

    topic_id: str
    topic_name: str
    similarity: float
    is_new: bool = False


class EmailTopicLink(BaseModel):
    """An email-to-topic association."""

    email_id: str
    topic_id: str


class EmailForTopics(BaseModel):
    """Email data needed for topic assignment."""

    id: str
    subject: str
    embedding: list[float] | None = None
    key_topics: list[str] = Field(default_factory=list)
