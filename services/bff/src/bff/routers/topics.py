"""BFF router for topic tracking endpoints."""

import structlog
from fastapi import APIRouter, HTTPException, Query

from bff.client import get_client
from bff.config import settings

logger = structlog.get_logger()

router = APIRouter(prefix="/api/v1/topics", tags=["topics"])


@router.get("")
async def list_topics(limit: int = Query(100), offset: int = Query(0)) -> list:
    """List all topics with email counts."""
    client = await get_client()
    resp = await client.get(f"{settings.topic_tracking_url}/topics", params={"limit": limit, "offset": offset})
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.json().get("detail", "upstream error"))
    return resp.json()


@router.get("/email/{email_id}")
async def get_email_topics(email_id: str) -> list:
    """Get all topics linked to a specific email."""
    client = await get_client()
    resp = await client.get(f"{settings.topic_tracking_url}/topics/email/{email_id}")
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.json().get("detail", "upstream error"))
    return resp.json()


@router.post("/assign/{email_id}")
async def assign_topics(email_id: str) -> list:
    """Trigger topic assignment for an email."""
    client = await get_client()
    resp = await client.post(f"{settings.topic_tracking_url}/topics/assign/{email_id}")
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.json().get("detail", "upstream error"))
    return resp.json()


@router.get("/{topic_id}")
async def get_topic(topic_id: str) -> dict:
    """Get a single topic by ID."""
    client = await get_client()
    resp = await client.get(f"{settings.topic_tracking_url}/topics/{topic_id}")
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.json().get("detail", "upstream error"))
    return resp.json()


@router.delete("/{topic_id}", status_code=204)
async def delete_topic(topic_id: str) -> None:
    """Delete a topic by ID."""
    client = await get_client()
    resp = await client.delete(f"{settings.topic_tracking_url}/topics/{topic_id}")
    if resp.status_code not in (204, 200):
        raise HTTPException(status_code=resp.status_code, detail=resp.json().get("detail", "upstream error"))


@router.get("/{topic_id}/emails")
async def get_topic_emails(topic_id: str, limit: int = Query(100)) -> list:
    """Get email IDs linked to a topic."""
    client = await get_client()
    resp = await client.get(f"{settings.topic_tracking_url}/topics/{topic_id}/emails", params={"limit": limit})
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.json().get("detail", "upstream error"))
    return resp.json()
