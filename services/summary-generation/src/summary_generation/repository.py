"""Database repository for the summary generation service."""

import json
from datetime import date

import asyncpg
import structlog

from summary_generation.config import settings
from summary_generation.schemas import EmailDigestEntry, Summary, SummaryListItem, SummaryType

logger = structlog.get_logger()

_pool: asyncpg.Pool | None = None


async def get_pool() -> asyncpg.Pool:
    """Get or create the asyncpg connection pool."""
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


async def get_emails_for_date(target_date: date) -> list[EmailDigestEntry]:
    """Fetch emails received on the given date, with their analysis data."""
    pool = await get_pool()
    rows = await pool.fetch(
        """
        SELECT e.id, e.sender, e.subject,
               COALESCE(ea.category, 'other') AS category,
               COALESCE(ea.urgency, 'normal') AS urgency,
               COALESCE(ea.summary, '') AS summary,
               COALESCE(ea.action_items, '[]'::jsonb) AS action_items,
               COALESCE(ea.key_topics, '{}') AS key_topics
        FROM emails e
        LEFT JOIN email_analyses ea ON e.id = ea.email_id
        WHERE e.received_at::date = $1
        ORDER BY e.received_at ASC
        """,
        target_date,
    )
    results = []
    for row in rows:
        action_items_raw = row["action_items"]
        if isinstance(action_items_raw, str):
            action_items_raw = json.loads(action_items_raw)
        action_descriptions = [item.get("description", "") for item in action_items_raw if isinstance(item, dict)]
        results.append(
            EmailDigestEntry(
                email_id=str(row["id"]),
                sender=row["sender"],
                subject=row["subject"],
                category=row["category"],
                urgency=row["urgency"],
                summary=row["summary"],
                action_items=action_descriptions,
                key_topics=list(row["key_topics"]),
            )
        )
    return results


async def get_emails_for_thread(thread_id: str) -> list[EmailDigestEntry]:
    """Fetch all emails in a thread, with their analysis data."""
    pool = await get_pool()
    rows = await pool.fetch(
        """
        SELECT e.id, e.sender, e.subject,
               COALESCE(ea.category, 'other') AS category,
               COALESCE(ea.urgency, 'normal') AS urgency,
               COALESCE(ea.summary, '') AS summary,
               COALESCE(ea.action_items, '[]'::jsonb) AS action_items,
               COALESCE(ea.key_topics, '{}') AS key_topics
        FROM emails e
        LEFT JOIN email_analyses ea ON e.id = ea.email_id
        WHERE e.thread_id = $1
        ORDER BY e.received_at ASC
        """,
        thread_id,
    )
    results = []
    for row in rows:
        action_items_raw = row["action_items"]
        if isinstance(action_items_raw, str):
            action_items_raw = json.loads(action_items_raw)
        action_descriptions = [item.get("description", "") for item in action_items_raw if isinstance(item, dict)]
        results.append(
            EmailDigestEntry(
                email_id=str(row["id"]),
                sender=row["sender"],
                subject=row["subject"],
                category=row["category"],
                urgency=row["urgency"],
                summary=row["summary"],
                action_items=action_descriptions,
                key_topics=list(row["key_topics"]),
            )
        )
    return results


async def get_summary(summary_type: SummaryType, target_date: date) -> Summary | None:
    """Fetch a summary by type and date."""
    pool = await get_pool()
    row = await pool.fetchrow(
        """
        SELECT s.id, s.summary_type, s.date, s.markdown_body, s.embedding, s.diff_hash, s.created_at
        FROM summaries s
        WHERE s.summary_type = $1 AND s.date = $2
        """,
        summary_type.value,
        target_date,
    )
    if row is None:
        return None
    topic_ids = await _get_topic_ids_for_summary(str(row["id"]))
    embedding = list(row["embedding"]) if row["embedding"] is not None else None
    return Summary(
        id=str(row["id"]),
        summary_type=row["summary_type"],
        date=row["date"],
        markdown_body=row["markdown_body"],
        embedding=embedding,
        diff_hash=row["diff_hash"],
        topic_ids=topic_ids,
        created_at=row["created_at"],
    )


async def get_summary_by_id(summary_id: str) -> Summary | None:
    """Fetch a summary by its ID."""
    pool = await get_pool()
    row = await pool.fetchrow(
        """
        SELECT id, summary_type, date, markdown_body, embedding, diff_hash, created_at
        FROM summaries
        WHERE id = $1
        """,
        summary_id,
    )
    if row is None:
        return None
    topic_ids = await _get_topic_ids_for_summary(str(row["id"]))
    embedding = list(row["embedding"]) if row["embedding"] is not None else None
    return Summary(
        id=str(row["id"]),
        summary_type=row["summary_type"],
        date=row["date"],
        markdown_body=row["markdown_body"],
        embedding=embedding,
        diff_hash=row["diff_hash"],
        topic_ids=topic_ids,
        created_at=row["created_at"],
    )


async def list_summaries(limit: int = 30, offset: int = 0) -> list[SummaryListItem]:
    """List summaries ordered by most recent date."""
    pool = await get_pool()
    rows = await pool.fetch(
        """
        SELECT id, summary_type, date, diff_hash, created_at
        FROM summaries
        ORDER BY date DESC, summary_type ASC
        LIMIT $1 OFFSET $2
        """,
        limit,
        offset,
    )
    return [
        SummaryListItem(
            id=str(row["id"]),
            summary_type=row["summary_type"],
            date=row["date"],
            diff_hash=row["diff_hash"],
            created_at=row["created_at"],
        )
        for row in rows
    ]


async def store_summary(
    summary_type: SummaryType,
    target_date: date,
    markdown_body: str,
    diff_hash: str,
    embedding: list[float] | None = None,
) -> str:
    """Store or update a summary. Returns the summary ID."""
    pool = await get_pool()
    embedding_str = "[" + ",".join(str(v) for v in embedding) + "]" if embedding else None
    row = await pool.fetchrow(
        """
        INSERT INTO summaries (summary_type, date, markdown_body, embedding, diff_hash)
        VALUES ($1, $2, $3, $4::vector, $5)
        ON CONFLICT (summary_type, date) DO UPDATE SET
            markdown_body = EXCLUDED.markdown_body,
            embedding = EXCLUDED.embedding,
            diff_hash = EXCLUDED.diff_hash
        RETURNING id
        """,
        summary_type.value,
        target_date,
        markdown_body,
        embedding_str,
        diff_hash,
    )
    summary_id = str(row["id"])
    logger.info("summary stored", summary_id=summary_id, summary_type=summary_type, date=str(target_date))
    return summary_id


async def link_summary_topics(summary_id: str, topic_ids: list[str]) -> None:
    """Link a summary to topics (replaces existing links)."""
    pool = await get_pool()
    await pool.execute("DELETE FROM summary_topics WHERE summary_id = $1", summary_id)
    for topic_id in topic_ids:
        await pool.execute(
            """
            INSERT INTO summary_topics (summary_id, topic_id)
            VALUES ($1, $2)
            ON CONFLICT DO NOTHING
            """,
            summary_id,
            topic_id,
        )


async def get_topic_ids_for_date(target_date: date) -> list[str]:
    """Get all topic IDs linked to emails received on the given date."""
    pool = await get_pool()
    rows = await pool.fetch(
        """
        SELECT DISTINCT et.topic_id
        FROM email_topics et
        JOIN emails e ON et.email_id = e.id
        WHERE e.received_at::date = $1
        """,
        target_date,
    )
    return [str(row["topic_id"]) for row in rows]


async def _get_topic_ids_for_summary(summary_id: str) -> list[str]:
    """Get topic IDs linked to a summary."""
    pool = await get_pool()
    rows = await pool.fetch(
        "SELECT topic_id FROM summary_topics WHERE summary_id = $1",
        summary_id,
    )
    return [str(row["topic_id"]) for row in rows]
