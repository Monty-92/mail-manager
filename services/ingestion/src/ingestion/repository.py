import asyncpg
import structlog

from ingestion.config import settings
from ingestion.schemas import EmailProvider, RawEmail, StoredEmail

logger = structlog.get_logger()

_pool: asyncpg.Pool | None = None


# Columns shared in list queries (excludes html_body for performance)
_EMAIL_LIST_COLS = (
    "id, provider, external_id, thread_id, sender, recipients, subject, received_at, labels, markdown_body, created_at"
)
# All columns for single-email detail
_EMAIL_DETAIL_COLS = (
    "id, provider, external_id, thread_id, sender, recipients, subject, received_at, labels, markdown_body, html_body, created_at"
)


def _row_to_stored_email(row: asyncpg.Record) -> StoredEmail:
    """Convert a database row to a StoredEmail model."""
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
        html_body=row.get("html_body", ""),
        created_at=row["created_at"],
    )


async def get_pool() -> asyncpg.Pool:
    """Get or create the connection pool."""
    global _pool
    if _pool is None:
        dsn = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
        _pool = await asyncpg.create_pool(dsn, min_size=2, max_size=10, command_timeout=60)
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
    """Insert an email or update html_body / labels if changed.

    Returns the StoredEmail if inserted/updated, None if it was a duplicate with no changes.
    """
    pool = await get_pool()
    row = await pool.fetchrow(
        """
        INSERT INTO emails (provider, external_id, thread_id, sender, recipients, subject, received_at, labels, markdown_body, html_body)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
        ON CONFLICT (provider, external_id) DO UPDATE SET
            labels = EXCLUDED.labels,
            html_body = CASE WHEN emails.html_body = '' AND EXCLUDED.html_body != '' THEN EXCLUDED.html_body ELSE emails.html_body END
        WHERE emails.labels IS DISTINCT FROM EXCLUDED.labels
           OR (emails.html_body = '' AND EXCLUDED.html_body != '')
        RETURNING id, provider, external_id, thread_id, sender, recipients, subject, received_at, labels, markdown_body, html_body, created_at
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
        email.html_body,
    )
    if row is None:
        return None
    return _row_to_stored_email(row)


async def get_email_by_external_id(provider: EmailProvider, external_id: str) -> StoredEmail | None:
    """Fetch a single email by provider + external_id."""
    pool = await get_pool()
    row = await pool.fetchrow(
        f"""
        SELECT {_EMAIL_DETAIL_COLS}
        FROM emails
        WHERE provider = $1 AND external_id = $2
        """,
        provider.value,
        external_id,
    )
    if row is None:
        return None
    return _row_to_stored_email(row)


async def get_email_by_id(email_id: str) -> StoredEmail | None:
    """Fetch a single email by internal UUID."""
    pool = await get_pool()
    row = await pool.fetchrow(
        f"""
        SELECT {_EMAIL_DETAIL_COLS}
        FROM emails
        WHERE id = $1
        """,
        email_id,
    )
    if row is None:
        return None
    return _row_to_stored_email(row)


async def list_emails(
    *,
    limit: int = 50,
    offset: int = 0,
    provider: str | None = None,
    search: str | None = None,
    label: str | None = None,
) -> tuple[list[StoredEmail], int]:
    """List emails with pagination, optional provider/label filter, and text search.
    Returns (emails, total_count)."""
    pool = await get_pool()

    conditions: list[str] = []
    params: list[str | int] = []
    idx = 1

    if provider:
        conditions.append(f"provider = ${idx}")
        params.append(provider)
        idx += 1

    if label:
        conditions.append(f"${idx} = ANY(labels)")
        params.append(label)
        idx += 1

    if search:
        conditions.append(f"(subject ILIKE ${idx} OR sender ILIKE ${idx} OR markdown_body ILIKE ${idx})")
        params.append(f"%{search}%")
        idx += 1

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    count_row = await pool.fetchrow(f"SELECT COUNT(*) AS cnt FROM emails {where}", *params)
    total = count_row["cnt"] if count_row else 0

    params.append(limit)
    limit_idx = idx
    idx += 1
    params.append(offset)
    offset_idx = idx

    rows = await pool.fetch(
        f"""
        SELECT {_EMAIL_LIST_COLS}
        FROM emails {where}
        ORDER BY received_at DESC
        LIMIT ${limit_idx} OFFSET ${offset_idx}
        """,
        *params,
    )
    return [_row_to_stored_email(r) for r in rows], total


async def get_distinct_labels() -> list[str]:
    """Get all distinct labels across all emails."""
    pool = await get_pool()
    rows = await pool.fetch("SELECT DISTINCT unnest(labels) AS label FROM emails ORDER BY label")
    return [row["label"] for row in rows]


async def get_emails_with_unresolved_labels(provider: str) -> list[dict]:
    """Get emails that still have provider-generated label IDs (e.g. Gmail's Label_XXXXXX)."""
    pool = await get_pool()
    rows = await pool.fetch(
        "SELECT id, labels FROM emails WHERE provider = $1 AND EXISTS "
        "(SELECT 1 FROM unnest(labels) AS l WHERE l LIKE 'Label\_%')",
        provider,
    )
    return [dict(r) for r in rows]


async def update_email_labels(email_id: str, labels: list[str]) -> None:
    """Update the labels array for a single email."""
    pool = await get_pool()
    await pool.execute("UPDATE emails SET labels = $1 WHERE id = $2", labels, email_id)


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
