import json

import structlog

from preprocessing.cleaner import prepare_embedding_text
from preprocessing.embedder import generate_embedding
from preprocessing.events import publish_preprocessed
from preprocessing.repository import get_email_by_id, get_pool, store_embedding
from preprocessing.schemas import EmailEvent, PreprocessingStatus, PreprocessResult

logger = structlog.get_logger()


async def preprocess_email(email_id: str) -> PreprocessResult:
    """Run the full preprocessing pipeline for a single email.

    1. Fetch email from DB
    2. Clean and prepare text
    3. Generate embedding via Ollama
    4. Store embedding in pgvector column
    5. Publish completion event
    """
    email = await get_email_by_id(email_id)
    if email is None:
        logger.warning("email not found", email_id=email_id)
        return PreprocessResult(
            email_id=email_id,
            cleaned_text="",
            embedding_dim=0,
            status=PreprocessingStatus.FAILED,
            error="email not found",
        )

    try:
        # Clean and prepare text
        cleaned = prepare_embedding_text(email.subject, email.sender, email.markdown_body)
        if not cleaned.strip():
            logger.warning("empty text after cleaning", email_id=email_id)
            return PreprocessResult(
                email_id=email_id,
                cleaned_text="",
                embedding_dim=0,
                status=PreprocessingStatus.FAILED,
                error="empty text after cleaning",
            )

        # Generate embedding
        result = await generate_embedding(cleaned)

        # Store in DB
        stored = await store_embedding(email_id, result.embedding)
        if not stored:
            logger.error("failed to store embedding", email_id=email_id)
            return PreprocessResult(
                email_id=email_id,
                cleaned_text=cleaned,
                embedding_dim=len(result.embedding),
                status=PreprocessingStatus.FAILED,
                error="failed to store embedding",
            )

        # Publish success event
        await publish_preprocessed(email_id, PreprocessingStatus.COMPLETED.value)
        await _write_pipeline_event(email_id, "preprocessed", {"embedding_dim": len(result.embedding)})

        logger.info("email preprocessed", email_id=email_id, embedding_dim=len(result.embedding))
        return PreprocessResult(
            email_id=email_id,
            cleaned_text=cleaned,
            embedding_dim=len(result.embedding),
            status=PreprocessingStatus.COMPLETED,
        )

    except Exception as exc:
        logger.exception("preprocessing failed", email_id=email_id)
        await publish_preprocessed(email_id, PreprocessingStatus.FAILED.value)
        return PreprocessResult(
            email_id=email_id,
            cleaned_text="",
            embedding_dim=0,
            status=PreprocessingStatus.FAILED,
            error=str(exc),
        )


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


async def handle_new_email_event(event: EmailEvent) -> None:
    """Callback for Redis subscriber — process a new email event."""
    logger.info("received new email event", email_id=event.id, subject=event.subject)
    await preprocess_email(event.id)
