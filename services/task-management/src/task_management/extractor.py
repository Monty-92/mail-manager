"""Task extraction from LLM analysis action items."""

import json

import structlog

from task_management.events import publish_task_created
from task_management.repository import create_task, get_action_items_for_email, get_pool, get_tasks_for_email
from task_management.schemas import AnalyzedEvent, TaskCreate, TaskExtractionResult, TaskPriority

logger = structlog.get_logger()

# Map urgency levels to task priority
_URGENCY_TO_PRIORITY: dict[str, TaskPriority] = {
    "critical": TaskPriority.HIGH,
    "high": TaskPriority.HIGH,
    "normal": TaskPriority.MEDIUM,
    "low": TaskPriority.LOW,
    "none": TaskPriority.NONE,
}


async def extract_tasks_from_email(email_id: str, urgency: str = "normal") -> TaskExtractionResult:
    """Extract tasks from an email's LLM analysis action items.

    Skips extraction if tasks already exist for the email (idempotent).
    """
    # Check if tasks already exist for this email
    existing = await get_tasks_for_email(email_id)
    if existing:
        logger.debug("tasks already exist for email, skipping", email_id=email_id, count=len(existing))
        return TaskExtractionResult(email_id=email_id, tasks_created=0)

    action_items = await get_action_items_for_email(email_id)
    if not action_items:
        logger.debug("no action items for email", email_id=email_id)
        return TaskExtractionResult(email_id=email_id, tasks_created=0)

    priority = _URGENCY_TO_PRIORITY.get(urgency, TaskPriority.MEDIUM)
    created_count = 0

    for item in action_items:
        if not item.description.strip():
            continue
        task = await create_task(
            TaskCreate(
                title=item.description[:200],
                notes=f"Extracted from email: {email_id}",
                priority=priority,
                source_email_id=email_id,
            )
        )
        await publish_task_created(task.id, email_id)
        created_count += 1

    logger.info("tasks extracted from email", email_id=email_id, tasks_created=created_count)
    if created_count > 0:
        await _write_pipeline_event(email_id, "tasks_extracted", {"tasks_created": created_count})
    return TaskExtractionResult(email_id=email_id, tasks_created=created_count)


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


async def handle_analyzed_event(event: AnalyzedEvent) -> None:
    """Callback for Redis subscriber — extract tasks from newly analyzed emails."""
    await extract_tasks_from_email(event.email_id, urgency=event.urgency)
