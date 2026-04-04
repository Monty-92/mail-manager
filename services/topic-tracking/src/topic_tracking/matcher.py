"""Topic matching and assignment pipeline."""

from datetime import date, timezone, datetime

import structlog

from topic_tracking.config import settings
from topic_tracking.repository import (
    create_topic,
    find_similar_topics,
    find_topic_by_name,
    get_email_for_topics,
    link_email_topic,
    update_topic_snapshot,
)
from topic_tracking.schemas import AnalyzedEvent, TopicMatch, TopicSnapshot

logger = structlog.get_logger()

SIMILARITY_THRESHOLD = 0.5  # Minimum cosine similarity to consider a match


async def assign_topics_for_email(email_id: str) -> list[TopicMatch]:
    """Assign topics to an email based on its analysis key_topics and embedding.

    Strategy:
    1. For each key_topic from the LLM analysis:
       a. Check for exact name match in topics table
       b. If not found and email has embedding, check for similar topics by embedding
       c. If still no match, create a new topic with the email's embedding
    2. Link email to each matched/created topic via email_topics
    3. Update topic snapshots with current date stats
    """
    email = await get_email_for_topics(email_id)
    if email is None:
        logger.warning("email not found for topic assignment", email_id=email_id)
        return []

    if not email.key_topics:
        logger.debug("no key_topics for email, skipping", email_id=email_id)
        return []

    matches: list[TopicMatch] = []
    today = date.today().isoformat()

    for topic_name in email.key_topics:
        topic_name = topic_name.strip()
        if not topic_name:
            continue

        # 1. Try exact name match
        existing = await find_topic_by_name(topic_name)
        if existing:
            await link_email_topic(email_id, existing.id)
            matches.append(TopicMatch(
                topic_id=existing.id,
                topic_name=existing.name,
                similarity=1.0,
                is_new=False,
            ))
            await _update_snapshot(existing.id, today, email.subject)
            continue

        # 2. Try embedding similarity if we have an embedding
        if email.embedding:
            similar = await find_similar_topics(email.embedding, threshold=SIMILARITY_THRESHOLD, limit=1)
            if similar:
                best_topic, similarity = similar[0]
                await link_email_topic(email_id, best_topic.id)
                matches.append(TopicMatch(
                    topic_id=best_topic.id,
                    topic_name=best_topic.name,
                    similarity=similarity,
                    is_new=False,
                ))
                await _update_snapshot(best_topic.id, today, email.subject)
                continue

        # 3. Create new topic
        new_topic = await create_topic(name=topic_name, embedding=email.embedding)
        await link_email_topic(email_id, new_topic.id)
        matches.append(TopicMatch(
            topic_id=new_topic.id,
            topic_name=new_topic.name,
            similarity=1.0,
            is_new=True,
        ))
        await _update_snapshot(new_topic.id, today, email.subject)

    logger.info(
        "topics assigned",
        email_id=email_id,
        topic_count=len(matches),
        new_topics=sum(1 for m in matches if m.is_new),
    )
    return matches


async def handle_analyzed_event(event: AnalyzedEvent) -> None:
    """Callback for Redis subscriber — assign topics to newly analyzed emails."""
    await assign_topics_for_email(event.email_id)


async def _update_snapshot(topic_id: str, today: str, subject: str) -> None:
    """Update topic snapshot for today. Appends a simple daily snapshot."""
    snapshot = TopicSnapshot(
        date=today,
        email_count=1,
        sample_subjects=[subject[:100]] if subject else [],
    )
    await update_topic_snapshot(topic_id, snapshot)
