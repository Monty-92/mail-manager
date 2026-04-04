import asyncpg
import structlog

from preprocessing.config import settings
from preprocessing.schemas import EmailRecord

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


async def get_email_by_id(email_id: str) -> EmailRecord | None:
    """Fetch an email by its UUID."""
    pool = await get_pool()
    row = await pool.fetchrow(
        """
        SELECT id, provider, external_id, sender, subject, markdown_body, received_at
        FROM emails
        WHERE id = $1
        """,
        email_id,
    )
    if row is None:
        return None
    return EmailRecord(
        id=str(row["id"]),
        provider=row["provider"],
        external_id=row["external_id"],
        sender=row["sender"],
        subject=row["subject"],
        markdown_body=row["markdown_body"],
        received_at=row["received_at"],
    )


async def get_unprocessed_emails(limit: int = 50) -> list[EmailRecord]:
    """Fetch emails that have no embedding yet."""
    pool = await get_pool()
    rows = await pool.fetch(
        """
        SELECT id, provider, external_id, sender, subject, markdown_body, received_at
        FROM emails
        WHERE embedding IS NULL
        ORDER BY received_at DESC
        LIMIT $1
        """,
        limit,
    )
    return [
        EmailRecord(
            id=str(row["id"]),
            provider=row["provider"],
            external_id=row["external_id"],
            sender=row["sender"],
            subject=row["subject"],
            markdown_body=row["markdown_body"],
            received_at=row["received_at"],
        )
        for row in rows
    ]


async def store_embedding(email_id: str, embedding: list[float]) -> bool:
    """Store the embedding vector for an email. Returns True if updated."""
    pool = await get_pool()
    result = await pool.execute(
        """
        UPDATE emails SET embedding = $1 WHERE id = $2
        """,
        str(embedding),
        email_id,
    )
    return result == "UPDATE 1"
