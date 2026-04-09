"""Summary generation orchestration pipeline."""

import hashlib
from datetime import date

import structlog

from summary_generation.llm_client import NOISE_CATEGORIES, generate_daily_summary, generate_embedding, generate_thread_summary
from summary_generation.repository import (
    get_emails_for_date,
    get_emails_for_thread,
    get_summary,
    get_topic_ids_for_date,
    link_summary_topics,
    store_summary,
)
from summary_generation.schemas import SummaryResult, SummaryType

logger = structlog.get_logger()


def _compute_diff_hash(content: str) -> str:
    """Compute a SHA-256 hash for change detection."""
    return hashlib.sha256(content.encode()).hexdigest()[:16]


async def generate_daily(target_date: date, summary_type: SummaryType) -> SummaryResult:
    """Generate (or regenerate) a daily summary for the given date and type.

    Pipeline:
    1. Fetch emails + analyses for the date
    2. Build LLM prompt and generate Markdown summary
    3. Generate embedding for the summary
    4. Compute diff hash
    5. Store summary (upsert on type+date)
    6. Link summary to topics from that date's emails
    """
    entries = await get_emails_for_date(target_date)

    if not entries:
        logger.info("no emails for date, skipping summary", date=str(target_date), type=summary_type)
        return SummaryResult(
            summary_type=summary_type,
            date=target_date,
            email_count=0,
            error="no emails found for this date",
        )

    # Split into substantive emails (sent to LLM in full) and noise (counted only)
    content_entries = [e for e in entries if e.category.lower() not in NOISE_CATEGORIES]
    noise_entries = [e for e in entries if e.category.lower() in NOISE_CATEGORIES]

    # Check if existing summary has same content
    existing = await get_summary(summary_type, target_date)
    is_regenerated = existing is not None

    markdown_body = await generate_daily_summary(
        summary_type=summary_type.value,
        target_date=str(target_date),
        entries=content_entries,
        noise_entries=noise_entries,
    )

    diff_hash = _compute_diff_hash(markdown_body)

    # Skip storage if content hasn't changed
    if existing and existing.diff_hash == diff_hash:
        logger.info("summary unchanged, skipping update", date=str(target_date), type=summary_type)
        return SummaryResult(
            summary_id=existing.id,
            summary_type=summary_type,
            date=target_date,
            email_count=len(entries),
            topic_count=len(existing.topic_ids),
            is_regenerated=False,
        )

    embedding = await generate_embedding(markdown_body)

    summary_id = await store_summary(
        summary_type=summary_type,
        target_date=target_date,
        markdown_body=markdown_body,
        diff_hash=diff_hash,
        embedding=embedding,
    )

    # Link to topics from emails of that date
    topic_ids = await get_topic_ids_for_date(target_date)
    if topic_ids:
        await link_summary_topics(summary_id, topic_ids)

    logger.info(
        "daily summary generated",
        summary_id=summary_id,
        date=str(target_date),
        type=summary_type,
        email_count=len(entries),
        topic_count=len(topic_ids),
        is_regenerated=is_regenerated,
    )

    return SummaryResult(
        summary_id=summary_id,
        summary_type=summary_type,
        date=target_date,
        email_count=len(entries),
        topic_count=len(topic_ids),
        is_regenerated=is_regenerated,
    )


async def generate_thread(thread_id: str) -> str:
    """Generate a summary for an email thread. Returns Markdown text.

    Does not store — thread summaries are generated on demand.
    """
    entries = await get_emails_for_thread(thread_id)

    if not entries:
        logger.warning("no emails found for thread", thread_id=thread_id)
        return ""

    markdown = await generate_thread_summary(entries)
    logger.info("thread summary generated", thread_id=thread_id, email_count=len(entries))
    return markdown
