"""BFF router for calendar operations (proxy to calendar-sync service)."""

import structlog
from fastapi import APIRouter, HTTPException, Query

from bff.client import get_client
from bff.config import settings

logger = structlog.get_logger()

router = APIRouter(prefix="/api/v1/calendar", tags=["calendar"])


@router.get("/events")
async def list_events(
    start_after: str | None = Query(None),
    end_before: str | None = Query(None),
    provider: str | None = Query(None),
    limit: int = Query(200),
) -> list[dict]:
    """List calendar events."""
    client = await get_client()
    params: dict[str, str | int] = {"limit": limit}
    if start_after:
        params["start_after"] = start_after
    if end_before:
        params["end_before"] = end_before
    if provider:
        params["provider"] = provider
    resp = await client.get(f"{settings.calendar_sync_url}/calendar/events", params=params)
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.json().get("detail", "upstream error"))
    return resp.json()


@router.get("/sources")
async def list_sources() -> list[dict]:
    """List calendar sources."""
    client = await get_client()
    resp = await client.get(f"{settings.calendar_sync_url}/calendar/sources")
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.json().get("detail", "upstream error"))
    return resp.json()


@router.post("/sync")
async def sync_calendar(body: dict | None = None) -> list[dict]:
    """Trigger calendar sync."""
    client = await get_client()
    resp = await client.post(f"{settings.calendar_sync_url}/calendar/sync", json=body or {})
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.json().get("detail", "upstream error"))
    return resp.json()


@router.delete("/events/{event_id}")
async def delete_event(event_id: str) -> dict:
    """Delete a calendar event."""
    client = await get_client()
    resp = await client.delete(f"{settings.calendar_sync_url}/calendar/events/{event_id}")
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.json().get("detail", "upstream error"))
    return resp.json()
