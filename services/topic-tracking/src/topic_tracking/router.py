"""FastAPI router for the topic tracking service."""

import structlog
from fastapi import APIRouter, HTTPException

from topic_tracking.matcher import assign_topics_for_email
from topic_tracking.repository import (
    delete_topic,
    get_email_ids_for_topic,
    get_topic_by_id,
    get_topics_for_email,
    list_topics,
)
from topic_tracking.schemas import Topic, TopicMatch, TopicSummary

logger = structlog.get_logger()

router = APIRouter(prefix="/topics", tags=["topics"])


@router.get("", response_model=list[TopicSummary])
async def list_all_topics(limit: int = 100, offset: int = 0) -> list[TopicSummary]:
    """List all topics with email counts."""
    return await list_topics(limit=limit, offset=offset)


@router.get("/email/{email_id}", response_model=list[TopicSummary])
async def get_email_topics(email_id: str) -> list[TopicSummary]:
    """Get all topics linked to a specific email."""
    return await get_topics_for_email(email_id)


@router.post("/assign/{email_id}", response_model=list[TopicMatch])
async def assign_topics(email_id: str) -> list[TopicMatch]:
    """Manually trigger topic assignment for an email."""
    return await assign_topics_for_email(email_id)


@router.get("/{topic_id}", response_model=Topic)
async def get_topic(topic_id: str) -> Topic:
    """Get a single topic by ID with full details."""
    topic = await get_topic_by_id(topic_id)
    if topic is None:
        raise HTTPException(status_code=404, detail="topic not found")
    return topic


@router.delete("/{topic_id}", status_code=204)
async def remove_topic(topic_id: str) -> None:
    """Delete a topic by ID."""
    deleted = await delete_topic(topic_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="topic not found")


@router.get("/{topic_id}/emails", response_model=list[str])
async def get_topic_emails(topic_id: str, limit: int = 100) -> list[str]:
    """Get email IDs linked to a topic."""
    return await get_email_ids_for_topic(topic_id, limit=limit)
