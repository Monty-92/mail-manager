"""Database repository for the topic tracking service."""

import json
from datetime import date

import asyncpg
import structlog

from topic_tracking.config import settings
from topic_tracking.schemas import EmailForTopics, EmailTopicLink, Topic, TopicSnapshot, TopicSummary

logger = structlog.get_logger()

_pool: asyncpg.Pool | None = None


async def get_pool() -> asyncpg.Pool:
    """Get or create the asyncpg connection pool."""
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


async def get_email_for_topics(email_id: str) -> EmailForTopics | None:
    """Fetch email data needed for topic assignment (subject, embedding, analysis key_topics)."""
    pool = await get_pool()
    row = await pool.fetchrow(
        """
        SELECT e.id, e.subject, e.embedding::float[] AS embedding,
               COALESCE(ea.key_topics, '{}') AS key_topics
        FROM emails e
        LEFT JOIN email_analyses ea ON e.id = ea.email_id
        WHERE e.id = $1
        """,
        email_id,
    )
    if row is None:
        return None
    embedding = list(row["embedding"]) if row["embedding"] is not None else None
    return EmailForTopics(
        id=str(row["id"]),
        subject=row["subject"],
        embedding=embedding,
        key_topics=list(row["key_topics"]),
    )


async def find_topic_by_name(name: str) -> Topic | None:
    """Find a topic by exact name (case-insensitive)."""
    pool = await get_pool()
    row = await pool.fetchrow(
        "SELECT id, name, embedding::float[] AS embedding, snapshots, created_at, updated_at FROM topics WHERE LOWER(name) = LOWER($1)",
        name,
    )
    if row is None:
        return None
    return _row_to_topic(row)


async def find_similar_topics(embedding: list[float], threshold: float = 0.3, limit: int = 5) -> list[tuple[Topic, float]]:
    """Find topics with embedding similarity above threshold using cosine distance.

    Returns list of (Topic, similarity_score) tuples sorted by similarity descending.
    Lower cosine distance = higher similarity, so similarity = 1 - distance.
    """
    pool = await get_pool()
    embedding_str = "[" + ",".join(str(v) for v in embedding) + "]"
    rows = await pool.fetch(
        """
        SELECT id, name, embedding::float[] AS embedding, snapshots, created_at, updated_at,
               1 - (embedding <=> $1::vector) AS similarity
        FROM topics
        WHERE embedding IS NOT NULL
          AND 1 - (embedding <=> $1::vector) > $2
        ORDER BY similarity DESC
        LIMIT $3
        """,
        embedding_str,
        threshold,
        limit,
    )
    results = []
    for row in rows:
        topic = _row_to_topic(row)
        results.append((topic, float(row["similarity"])))
    return results


async def create_topic(name: str, embedding: list[float] | None = None) -> Topic:
    """Create a new topic."""
    pool = await get_pool()
    embedding_str = "[" + ",".join(str(v) for v in embedding) + "]" if embedding else None
    row = await pool.fetchrow(
        """
        INSERT INTO topics (name, embedding, snapshots)
        VALUES ($1, $2::vector, '[]'::jsonb)
        RETURNING id, name, embedding, snapshots, created_at, updated_at
        """,
        name,
        embedding_str,
    )
    logger.info("topic created", topic_name=name, topic_id=str(row["id"]))
    return _row_to_topic(row)


async def update_topic_snapshot(topic_id: str, snapshot: TopicSnapshot) -> bool:
    """Append a snapshot to the topic's snapshots array and update timestamp."""
    pool = await get_pool()
    try:
        await pool.execute(
            """
            UPDATE topics
            SET snapshots = snapshots || $2::jsonb,
                updated_at = now()
            WHERE id = $1
            """,
            topic_id,
            json.dumps([snapshot.model_dump()]),
        )
        return True
    except Exception:
        logger.exception("failed to update topic snapshot", topic_id=topic_id)
        return False


async def link_email_topic(email_id: str, topic_id: str) -> bool:
    """Link an email to a topic (idempotent via ON CONFLICT)."""
    pool = await get_pool()
    try:
        await pool.execute(
            """
            INSERT INTO email_topics (email_id, topic_id)
            VALUES ($1, $2)
            ON CONFLICT DO NOTHING
            """,
            email_id,
            topic_id,
        )
        return True
    except Exception:
        logger.exception("failed to link email to topic", email_id=email_id, topic_id=topic_id)
        return False


async def get_topic_by_id(topic_id: str) -> Topic | None:
    """Fetch a single topic by ID, including email count."""
    pool = await get_pool()
    row = await pool.fetchrow(
        """
        SELECT t.id, t.name, t.embedding::float[] AS embedding, t.snapshots, t.created_at, t.updated_at,
               COUNT(et.email_id) AS email_count
        FROM topics t
        LEFT JOIN email_topics et ON t.id = et.topic_id
        WHERE t.id = $1
        GROUP BY t.id
        """,
        topic_id,
    )
    if row is None:
        return None
    topic = _row_to_topic(row)
    topic.email_count = int(row["email_count"])
    return topic


async def list_topics(limit: int = 100, offset: int = 0) -> list[TopicSummary]:
    """List all topics with email counts, ordered by most recent update."""
    pool = await get_pool()
    rows = await pool.fetch(
        """
        SELECT t.id, t.name, t.created_at, t.updated_at,
               COUNT(et.email_id) AS email_count
        FROM topics t
        LEFT JOIN email_topics et ON t.id = et.topic_id
        GROUP BY t.id
        ORDER BY t.updated_at DESC
        LIMIT $1 OFFSET $2
        """,
        limit,
        offset,
    )
    return [
        TopicSummary(
            id=str(row["id"]),
            name=row["name"],
            email_count=int(row["email_count"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
        for row in rows
    ]


async def get_topics_for_email(email_id: str) -> list[TopicSummary]:
    """Get all topics linked to a specific email."""
    pool = await get_pool()
    rows = await pool.fetch(
        """
        SELECT t.id, t.name, t.created_at, t.updated_at,
               COUNT(et2.email_id) AS email_count
        FROM email_topics et
        JOIN topics t ON et.topic_id = t.id
        LEFT JOIN email_topics et2 ON t.id = et2.topic_id
        WHERE et.email_id = $1
        GROUP BY t.id
        """,
        email_id,
    )
    return [
        TopicSummary(
            id=str(row["id"]),
            name=row["name"],
            email_count=int(row["email_count"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
        for row in rows
    ]


async def get_email_ids_for_topic(topic_id: str, limit: int = 100) -> list[str]:
    """Get email IDs linked to a specific topic."""
    pool = await get_pool()
    rows = await pool.fetch(
        "SELECT email_id FROM email_topics WHERE topic_id = $1 LIMIT $2",
        topic_id,
        limit,
    )
    return [str(row["email_id"]) for row in rows]


async def delete_topic(topic_id: str) -> bool:
    """Delete a topic. Junction table entries cascade."""
    pool = await get_pool()
    result = await pool.execute("DELETE FROM topics WHERE id = $1", topic_id)
    return result == "DELETE 1"


def _row_to_topic(row) -> Topic:
    """Convert a database row to a Topic model."""
    snapshots_raw = row["snapshots"] if row["snapshots"] else []
    if isinstance(snapshots_raw, str):
        snapshots_raw = json.loads(snapshots_raw)
    embedding = list(row["embedding"]) if row["embedding"] is not None else None
    return Topic(
        id=str(row["id"]),
        name=row["name"],
        embedding=embedding,
        snapshots=[TopicSnapshot(**s) for s in snapshots_raw],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )
