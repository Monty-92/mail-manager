"""Calendar sync service router."""

from datetime import datetime, timedelta, timezone
from uuid import UUID

import structlog
from fastapi import APIRouter, HTTPException, Query
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

from calendar_sync.calendar_repository import (
    delete_event,
    get_calendar_account,
    get_calendar_accounts,
    get_events,
    update_account_token,
    upsert_calendar_event,
)
from calendar_sync.config import settings
from calendar_sync.providers.google import GoogleCalendarProvider
from calendar_sync.providers.outlook import OutlookCalendarProvider
from calendar_sync.schemas import (
    CalendarEventResponse,
    CalendarSourceResponse,
    SyncCalendarRequest,
    SyncCalendarResponse,
)

logger = structlog.get_logger()

router = APIRouter(prefix="/calendar", tags=["calendar"])


async def _refresh_google_token(acct: dict) -> str:
    """Return a valid Google access token, refreshing if expired."""
    token_expiry = acct.get("token_expiry")
    access_token = acct["access_token"]
    refresh_token = acct.get("refresh_token")

    if token_expiry and token_expiry.replace(tzinfo=timezone.utc) > datetime.now(tz=timezone.utc) + timedelta(minutes=5):
        return access_token

    if not refresh_token:
        logger.warning("no refresh token, using existing access token", email=acct["email"])
        return access_token

    creds = Credentials(
        token=access_token,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
    )
    creds.refresh(Request())

    new_expiry = creds.expiry.replace(tzinfo=timezone.utc) if creds.expiry else None
    await update_account_token(str(acct["id"]), creds.token, new_expiry)
    logger.info("google token refreshed", email=acct["email"])
    return creds.token


def _event_to_response(e: dict) -> CalendarEventResponse:
    import json

    attendees = e["attendees"]
    if isinstance(attendees, str):
        attendees = json.loads(attendees)

    return CalendarEventResponse(
        id=str(e["id"]),
        provider=e["provider"],
        external_id=e["external_id"],
        calendar_id=e["calendar_id"],
        title=e["title"],
        description=e["description"],
        start_at=e["start_at"].isoformat() if isinstance(e["start_at"], datetime) else e["start_at"],
        end_at=e["end_at"].isoformat() if isinstance(e["end_at"], datetime) else e["end_at"],
        all_day=e["all_day"],
        location=e["location"],
        status=e["status"],
        organizer=e.get("organizer"),
        attendees=attendees,
        created_at=e["created_at"].isoformat() if isinstance(e["created_at"], datetime) else e["created_at"],
        updated_at=e["updated_at"].isoformat() if isinstance(e["updated_at"], datetime) else e["updated_at"],
    )


@router.get("/events")
async def list_events(
    start_after: str | None = Query(None),
    end_before: str | None = Query(None),
    provider: str | None = Query(None),
    limit: int = Query(200, ge=1, le=1000),
) -> list[CalendarEventResponse]:
    """List calendar events from the database."""
    sa = datetime.fromisoformat(start_after) if start_after else None
    eb = datetime.fromisoformat(end_before) if end_before else None
    events = await get_events(start_after=sa, end_before=eb, provider=provider, limit=limit)
    return [_event_to_response(e) for e in events]


@router.get("/sources")
async def list_sources() -> list[CalendarSourceResponse]:
    """List all calendar sources (connected accounts with calendar access)."""
    accounts = await get_calendar_accounts()
    sources = []
    for i, acct in enumerate(accounts):
        color = "#4285f4" if acct["provider"] == "gmail" else "#0078d4"
        sources.append(
            CalendarSourceResponse(
                id=str(acct["id"]),
                provider=acct["provider"],
                account_email=acct["email"],
                calendar_name=f"{acct['display_name'] or acct['email']} Calendar",
                color=color,
                enabled=True,
            )
        )
    return sources


@router.post("/sync")
async def sync_calendar(req: SyncCalendarRequest | None = None) -> list[SyncCalendarResponse]:
    """Sync calendar events from connected accounts."""
    if req and req.account_id:
        acct = await get_calendar_account(req.account_id)
        if not acct:
            raise HTTPException(status_code=404, detail="Account not found")
        accounts = [acct]
    else:
        accounts = await get_calendar_accounts()

    if not accounts:
        raise HTTPException(status_code=404, detail="No calendar accounts connected")

    results = []
    now = datetime.now(tz=timezone.utc)
    time_min = now - timedelta(days=30)
    time_max = now + timedelta(days=90)

    for acct in accounts:
        provider_type = acct["provider"]

        if provider_type == "gmail":
            access_token = await _refresh_google_token(acct)
            cal_provider = GoogleCalendarProvider(access_token)
        elif provider_type == "outlook":
            access_token = acct["access_token"]
            cal_provider = OutlookCalendarProvider(access_token)
        else:
            continue

        try:
            events = await cal_provider.fetch_events(calendar_id="primary", time_min=time_min, time_max=time_max)
        except Exception:
            logger.exception("calendar sync failed", provider=provider_type, email=acct["email"])
            continue

        synced = 0
        for ev in events:
            await upsert_calendar_event(
                provider=ev["provider"],
                external_id=ev["external_id"],
                calendar_id=ev["calendar_id"],
                title=ev["title"],
                description=ev["description"],
                start_at=ev["start_at"],
                end_at=ev["end_at"],
                all_day=ev["all_day"],
                location=ev["location"],
                status=ev["status"],
                organizer=ev.get("organizer"),
                attendees=ev.get("attendees", []),
            )
            synced += 1

        results.append(SyncCalendarResponse(synced=synced, provider=provider_type, account_email=acct["email"]))
        logger.info("calendar synced", provider=provider_type, email=acct["email"], synced=synced)

    return results


@router.delete("/events/{event_id}")
async def remove_event(event_id: UUID) -> dict:
    deleted = await delete_event(str(event_id))
    if not deleted:
        raise HTTPException(status_code=404, detail="Event not found")
    return {"detail": "Event deleted"}
