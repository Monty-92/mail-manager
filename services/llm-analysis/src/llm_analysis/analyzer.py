"""Email analysis pipeline — orchestrates LLM analysis of preprocessed emails."""

import json

import structlog

from llm_analysis.config import settings
from llm_analysis.llm_client import analyze_email_text
from llm_analysis.repository import get_email_by_id, get_pool, store_analysis
from llm_analysis.schemas import (
    ActionItem,
    AnalysisResult,
    EmailCategory,
    EmailForAnalysis,
    PreprocessedEvent,
    Sentiment,
    UrgencyLevel,
)

logger = structlog.get_logger()

# Valid enum values for safe parsing
_VALID_CATEGORIES = {e.value for e in EmailCategory}
_VALID_URGENCIES = {e.value for e in UrgencyLevel}
_VALID_SENTIMENTS = {e.value for e in Sentiment}


def _safe_category(value: str) -> EmailCategory:
    return EmailCategory(value) if value in _VALID_CATEGORIES else EmailCategory.OTHER


def _safe_urgency(value: str) -> UrgencyLevel:
    return UrgencyLevel(value) if value in _VALID_URGENCIES else UrgencyLevel.NORMAL


def _safe_sentiment(value: str) -> Sentiment:
    return Sentiment(value) if value in _VALID_SENTIMENTS else Sentiment.NEUTRAL


def _parse_action_items(raw: list) -> list[ActionItem]:
    """Parse action items from LLM response, tolerating malformed entries."""
    items = []
    for entry in raw:
        if isinstance(entry, dict) and "description" in entry:
            items.append(ActionItem(
                description=entry["description"],
                assignee=entry.get("assignee"),
                due_hint=entry.get("due_hint"),
            ))
        elif isinstance(entry, str):
            items.append(ActionItem(description=entry))
    return items


def parse_llm_response(email_id: str, raw: dict) -> AnalysisResult:
    """Parse raw LLM JSON response into a validated AnalysisResult.

    Tolerates missing or invalid fields by falling back to safe defaults.
    """
    return AnalysisResult(
        email_id=email_id,
        category=_safe_category(raw.get("category", "other")),
        urgency=_safe_urgency(raw.get("urgency", "normal")),
        summary=str(raw.get("summary", "")),
        action_items=_parse_action_items(raw.get("action_items", [])),
        key_topics=[str(t) for t in raw.get("key_topics", [])][:5],
        sentiment=_safe_sentiment(raw.get("sentiment", "neutral")),
        is_junk=bool(raw.get("is_junk", False)),
        confidence=min(max(float(raw.get("confidence", 0.0)), 0.0), 1.0),
        model_used=settings.ollama_model,
    )


async def analyze_email(email_id: str) -> AnalysisResult:
    """Run full analysis pipeline for a single email: fetch → LLM → store."""
    logger.info("analyzing email", email_id=email_id)

    email = await get_email_by_id(email_id)
    if email is None:
        logger.warning("email not found", email_id=email_id)
        return AnalysisResult(email_id=email_id, error="email not found")

    if not email.markdown_body.strip():
        logger.warning("email has empty body", email_id=email_id)
        return AnalysisResult(email_id=email_id, error="empty email body")

    try:
        raw_response = await analyze_email_text(
            sender=email.sender,
            recipients=", ".join(email.recipients),
            subject=email.subject,
            received_at=email.received_at.isoformat(),
            body=email.markdown_body,
        )
    except Exception:
        logger.exception("LLM analysis failed", email_id=email_id)
        return AnalysisResult(email_id=email_id, error="llm analysis failed")

    result = parse_llm_response(email_id, raw_response)

    stored = await store_analysis(result)
    if not stored:
        result.error = "failed to store analysis"
    else:
        await _write_pipeline_event(email_id, "analyzed", {"category": result.category.value, "urgency": result.urgency.value})

    return result


async def _write_pipeline_event(email_id: str, stage: str, details: dict) -> None:
    """Fire-and-forget insert into pipeline_events."""
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO pipeline_events (stage, email_id, details) VALUES ($1, $2::uuid, $3::jsonb)",
                stage, email_id, json.dumps(details),
            )
    except Exception:
        logger.warning("failed to write pipeline event", stage=stage, email_id=email_id)


async def handle_preprocessed_event(event: PreprocessedEvent) -> None:
    """Callback for Redis subscriber — analyze newly preprocessed emails."""
    if event.status != "completed":
        logger.debug("skipping non-completed event", email_id=event.email_id, status=event.status)
        return
    await analyze_email(event.email_id)
