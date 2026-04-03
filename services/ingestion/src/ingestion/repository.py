from datetime import datetime

import asyncpg
import structlog

from ingestion.config import settings
from ingestion.schemas import EmailProvider, RawEmail, StoredEmail

logger = structlog.get_logger()

_pool: asyncpg.Pool | None = None


async def get_pool() -> asyncpg.Pool:
    """Get or create the connection pool."""
    global _pool
    if _pool is None:
        dsn = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
        _pool = await asyncpg.create_pool(dsn, min_size=2, max_size=10)
        logger.info("database pool created")
    return _pool


async def close_pool() -> None:
    """Close the connection pool."""
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None
        logger.info("database pool closed")


async def upsert_email(email: RawEmail, markdown_body: str) -> StoredEmail | None:
    """Insert an email if it doesn't already exist (dedup by provider + external_id).

    Returns the StoredEmail if inserted, None if it was a duplicate.
    """
    pool = await get_pool()
    row = await pool.fetchrow(
        """
        INSERT INTO emails (provider, external_id, thread_id, sender, recipients, subject, received_at, labels, markdown_body)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
        ON CONFLICT (provider, external_id) DO NOTHING
        RETURNING id, provider, external_id, thread_id, sender, recipients, subject, received_at, labels, markdown_body, created_at
        """,
        email.provider.value,
        email.external_id,
        email.thread_id,
        email.sender,
        email.recipients,
        email.subject,
        email.received_at,
        email.labels,
        markdown_body,
    )
    if row is None:
        return None
    return StoredEmail(
        id=str(row["id"]),
        provider=EmailProvider(row["provider"]),
        external_id=row["external_id"],
        thread_id=row["thread_id"],
        sender=row["sender"],
        recipients=list(row["recipients"]),
        subject=row["subject"],
        received_at=row["received_at"],
        labels=list(row["labels"]),
        markdown_body=row["markdown_body"],
        created_at=row["created_at"],
    )


async def get_email_by_external_id(provider: EmailProvider, external_id: str) -> StoredEmail | None:
    """Fetch a single email by provider + external_id."""
    pool = await get_pool()
    row = await pool.fetchrow(
        """
        SELECT id, provider, external_id, thread_id, sender, recipients, subject, received_at, labels, markdown_body, created_at
        FROM emails
        WHERE provider = $1 AND external_id = $2
        """,
        provider.value,
        external_id,
    )
    if row is None:
        return None
    return StoredEmail(
        id=str(row["id"]),
        provider=EmailProvider(row["provider"]),
        external_id=row["external_id"],
        thread_id=row["thread_id"],
        sender=row["sender"],
        recipients=list(row["recipients"]),
        subject=row["subject"],
        received_at=row["received_at"],
        labels=list(row["labels"]),
        markdown_body=row["markdown_body"],
        created_at=row["created_at"],
    )


async def get_sync_state(provider: EmailProvider) -> dict[str, str | None]:
    """Get sync state for a provider from the sync_state table. Returns empty dict if not found."""
    pool = await get_pool()
    row = await pool.fetchrow(
        "SELECT history_id, delta_link, last_sync_at FROM sync_state WHERE provider = $1",
        provider.value,
    )
    if row is None:
        return {"history_id": None, "delta_link": None, "last_sync_at": None}
    return {
        "history_id": row["history_id"],
        "delta_link": row["delta_link"],
        "last_sync_at": row["last_sync_at"].isoformat() if row["last_sync_at"] else None,
    }


async def save_sync_state(
    provider: EmailProvider,
    *,
    history_id: str | None = None,
    delta_link: str | None = None,
) -> None:
    """Upsert sync state for a provider."""
    pool = await get_pool()
    await pool.execute(
        """
        INSERT INTO sync_state (provider, history_id, delta_link, last_sync_at)
        VALUES ($1, $2, $3, now())
        ON CONFLICT (provider) DO UPDATE SET
            history_id = COALESCE($2, sync_state.history_id),
            delta_link = COALESCE($3, sync_state.delta_link),
            last_sync_at = now()
        """,
        provider.value,
        history_id,
        delta_link,
    )
