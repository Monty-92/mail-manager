from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel


class EmailProvider(StrEnum):
    GMAIL = "gmail"
    OUTLOOK = "outlook"


class RawEmail(BaseModel):
    """Raw email data as fetched from a provider, before DB storage."""

    provider: EmailProvider
    external_id: str
    thread_id: str | None = None
    sender: str
    recipients: list[str] = []
    subject: str = ""
    received_at: datetime
    labels: list[str] = []
    html_body: str = ""
    text_body: str = ""


class StoredEmail(BaseModel):
    """Email record as stored in PostgreSQL."""

    id: str
    provider: EmailProvider
    external_id: str
    thread_id: str | None = None
    sender: str
    recipients: list[str] = []
    subject: str = ""
    received_at: datetime
    labels: list[str] = []
    markdown_body: str = ""
    html_body: str = ""
    created_at: datetime


class IngestResult(BaseModel):
    """Result of an ingestion run."""

    provider: EmailProvider
    total_fetched: int = 0
    new_stored: int = 0
    duplicates_skipped: int = 0


class OAuthTokens(BaseModel):
    """OAuth token pair for a provider."""

    access_token: str
    refresh_token: str | None = None
    token_expiry: datetime | None = None


class SyncState(BaseModel):
    """Tracks incremental sync state per provider."""

    provider: EmailProvider
    history_id: str | None = None  # Gmail history ID
    delta_link: str | None = None  # Outlook delta link
    last_sync_at: datetime | None = None
