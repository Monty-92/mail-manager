"""Database repository for the LLM analysis service."""

import json

import asyncpg
import structlog

from llm_analysis.config import settings
from llm_analysis.schemas import ActionItem, EmailForAnalysis, AnalysisResult, StoredAnalysis

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


async def get_email_by_id(email_id: str) -> EmailForAnalysis | None:
    """Fetch an email from the database for analysis."""
    pool = await get_pool()
    row = await pool.fetchrow(
        """
        SELECT id, provider, sender, recipients, subject, markdown_body, received_at
        FROM emails
        WHERE id = $1
        """,
        email_id,
    )
    if row is None:
        return None
    return EmailForAnalysis(
        id=str(row["id"]),
        provider=row["provider"],
        sender=row["sender"],
        recipients=list(row["recipients"]),
        subject=row["subject"],
        markdown_body=row["markdown_body"],
        received_at=row["received_at"],
    )


async def get_unanalyzed_emails(limit: int = 50) -> list[EmailForAnalysis]:
    """Fetch emails that have embeddings but no analysis yet."""
    pool = await get_pool()
    rows = await pool.fetch(
        """
        SELECT e.id, e.provider, e.sender, e.recipients, e.subject, e.markdown_body, e.received_at
        FROM emails e
        LEFT JOIN email_analyses ea ON e.id = ea.email_id
        WHERE e.embedding IS NOT NULL AND ea.id IS NULL
        ORDER BY e.received_at DESC
        LIMIT $1
        """,
        limit,
    )
    return [
        EmailForAnalysis(
            id=str(row["id"]),
            provider=row["provider"],
            sender=row["sender"],
            recipients=list(row["recipients"]),
            subject=row["subject"],
            markdown_body=row["markdown_body"],
            received_at=row["received_at"],
        )
        for row in rows
    ]


async def store_analysis(result: AnalysisResult) -> bool:
    """Store an analysis result in the database. Returns True on success."""
    pool = await get_pool()
    try:
        action_items_json = json.dumps([item.model_dump() for item in result.action_items])
        await pool.execute(
            """
            INSERT INTO email_analyses (
                email_id, category, urgency, summary, action_items,
                key_topics, sentiment, is_junk, confidence, model_used
            ) VALUES ($1, $2, $3, $4, $5::jsonb, $6, $7, $8, $9, $10)
            ON CONFLICT (email_id) DO UPDATE SET
                category = EXCLUDED.category,
                urgency = EXCLUDED.urgency,
                summary = EXCLUDED.summary,
                action_items = EXCLUDED.action_items,
                key_topics = EXCLUDED.key_topics,
                sentiment = EXCLUDED.sentiment,
                is_junk = EXCLUDED.is_junk,
                confidence = EXCLUDED.confidence,
                model_used = EXCLUDED.model_used,
                updated_at = now()
            """,
            result.email_id,
            result.category.value,
            result.urgency.value,
            result.summary,
            action_items_json,
            result.key_topics,
            result.sentiment.value,
            result.is_junk,
            result.confidence,
            result.model_used,
        )
        logger.info("analysis stored", email_id=result.email_id)
        return True
    except Exception:
        logger.exception("failed to store analysis", email_id=result.email_id)
        return False


async def get_analysis_by_email_id(email_id: str) -> StoredAnalysis | None:
    """Retrieve a stored analysis result for an email."""
    pool = await get_pool()
    row = await pool.fetchrow(
        """
        SELECT id, email_id, category, urgency, summary, action_items,
               key_topics, sentiment, is_junk, confidence, model_used,
               created_at, updated_at
        FROM email_analyses
        WHERE email_id = $1
        """,
        email_id,
    )
    if row is None:
        return None
    action_items_raw = json.loads(row["action_items"]) if isinstance(row["action_items"], str) else row["action_items"]
    return StoredAnalysis(
        id=str(row["id"]),
        email_id=str(row["email_id"]),
        category=row["category"],
        urgency=row["urgency"],
        summary=row["summary"],
        action_items=[ActionItem(**item) for item in action_items_raw],
        key_topics=list(row["key_topics"]),
        sentiment=row["sentiment"],
        is_junk=row["is_junk"],
        confidence=row["confidence"],
        model_used=row["model_used"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )
