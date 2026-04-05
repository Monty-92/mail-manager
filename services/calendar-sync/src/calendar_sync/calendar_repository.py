"""Repository for calendar_events and connected_accounts (read-only) operations."""

from datetime import datetime

import asyncpg
import structlog

from calendar_sync.config import settings

logger = structlog.get_logger()

_pool: asyncpg.Pool | None = None


async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        dsn = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
        _pool = await asyncpg.create_pool(dsn, min_size=2, max_size=10)
        logger.info("calendar-sync database pool created")
    return _pool


async def close_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


async def get_calendar_accounts() -> list[dict]:
    """Get all connected accounts that have calendar scopes."""
    pool = await get_pool()
    rows = await pool.fetch(
        """
        SELECT id, provider, email, display_name, access_token, refresh_token, token_expiry, scopes
        FROM connected_accounts
        WHERE scopes && ARRAY['https://www.googleapis.com/auth/calendar', 'Calendars.ReadWrite']::TEXT[]
        ORDER BY created_at
        """
    )
    return [dict(r) for r in rows]


async def get_calendar_account(account_id: str) -> dict | None:
    """Get a single connected account by ID."""
    pool = await get_pool()
    row = await pool.fetchrow(
        "SELECT id, provider, email, display_name, access_token, refresh_token, token_expiry, scopes "
        "FROM connected_accounts WHERE id = $1",
        account_id,
    )
    return dict(row) if row else None


async def update_account_token(account_id: str, access_token: str, token_expiry: datetime | None) -> None:
    """Persist a refreshed access token and expiry for a connected account."""
    pool = await get_pool()
    await pool.execute(
        "UPDATE connected_accounts SET access_token = $1, token_expiry = $2 WHERE id = $3",
        access_token,
        token_expiry,
        account_id,
    )


async def upsert_calendar_event(
    provider: str,
    external_id: str,
    calendar_id: str,
    title: str,
    description: str,
    start_at: datetime,
    end_at: datetime,
    all_day: bool,
    location: str,
    status: str,
    organizer: str | None,
    attendees: list,
) -> dict:
    """Insert or update a calendar event."""
    pool = await get_pool()
    import json

    attendees_json = json.dumps(attendees)
    row = await pool.fetchrow(
        """
        INSERT INTO calendar_events (provider, external_id, calendar_id, title, description, start_at, end_at, all_day, location, status, organizer, attendees)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12::jsonb)
        ON CONFLICT (provider, external_id) DO UPDATE SET
            title = EXCLUDED.title,
            description = EXCLUDED.description,
            start_at = EXCLUDED.start_at,
            end_at = EXCLUDED.end_at,
            all_day = EXCLUDED.all_day,
            location = EXCLUDED.location,
            status = EXCLUDED.status,
            organizer = EXCLUDED.organizer,
            attendees = EXCLUDED.attendees,
            updated_at = now()
        RETURNING id, provider, external_id, calendar_id, title, description, start_at, end_at, all_day, location, status, organizer, attendees, created_at, updated_at
        """,
        provider,
        external_id,
        calendar_id,
        title,
        description,
        start_at,
        end_at,
        all_day,
        location,
        status,
        organizer,
        attendees_json,
    )
    return dict(row)


async def get_events(
    start_after: datetime | None = None,
    end_before: datetime | None = None,
    provider: str | None = None,
    limit: int = 200,
) -> list[dict]:
    """Query calendar events with optional filters."""
    pool = await get_pool()
    conditions = []
    params: list = []
    idx = 1

    if start_after:
        conditions.append(f"end_at >= ${idx}")
        params.append(start_after)
        idx += 1
    if end_before:
        conditions.append(f"start_at <= ${idx}")
        params.append(end_before)
        idx += 1
    if provider:
        conditions.append(f"provider = ${idx}")
        params.append(provider)
        idx += 1

    where = "WHERE " + " AND ".join(conditions) if conditions else ""
    conditions.append(f"${idx}")
    params.append(limit)

    query = f"""
        SELECT id, provider, external_id, calendar_id, title, description, start_at, end_at,
               all_day, location, status, organizer, attendees, created_at, updated_at
        FROM calendar_events {where}
        ORDER BY start_at
        LIMIT ${idx}
    """
    rows = await pool.fetch(query, *params)
    return [dict(r) for r in rows]


async def delete_event(event_id: str) -> bool:
    pool = await get_pool()
    result = await pool.execute("DELETE FROM calendar_events WHERE id = $1", event_id)
    return result == "DELETE 1"
