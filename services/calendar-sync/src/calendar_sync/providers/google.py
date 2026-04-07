"""Google Calendar API v3 provider."""

from datetime import datetime, timezone

import httpx
import structlog

from calendar_sync.providers import BaseCalendarProvider

logger = structlog.get_logger()

GOOGLE_CALENDAR_API = "https://www.googleapis.com/calendar/v3"


class GoogleCalendarProvider(BaseCalendarProvider):
    def __init__(self, access_token: str) -> None:
        self._access_token = access_token

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._access_token}"}

    async def list_calendars(self) -> list[dict]:
        """List all calendars for this Google account."""
        calendars: list[dict] = []
        url = f"{GOOGLE_CALENDAR_API}/users/me/calendarList"
        params: dict[str, str] = {"maxResults": "250"}

        async with httpx.AsyncClient() as client:
            while url:
                resp = await client.get(url, headers=self._headers(), params=params, timeout=30.0)
                resp.raise_for_status()
                data = resp.json()

                for item in data.get("items", []):
                    calendars.append({
                        "external_id": item["id"],
                        "name": item.get("summary", item["id"]),
                        "color": item.get("backgroundColor", "#4285f4"),
                        "is_primary": item.get("primary", False),
                    })

                next_page = data.get("nextPageToken")
                if next_page:
                    params["pageToken"] = next_page
                else:
                    url = ""  # type: ignore[assignment]

        logger.info("google calendars listed", count=len(calendars))
        return calendars

    async def fetch_events(
        self, calendar_id: str = "primary", time_min: datetime | None = None, time_max: datetime | None = None
    ) -> list[dict]:
        params: dict[str, str] = {"singleEvents": "true", "orderBy": "startTime", "maxResults": "250"}
        if time_min:
            params["timeMin"] = time_min.isoformat()
        if time_max:
            params["timeMax"] = time_max.isoformat()

        events: list[dict] = []
        url = f"{GOOGLE_CALENDAR_API}/calendars/{calendar_id}/events"

        async with httpx.AsyncClient() as client:
            while url:
                resp = await client.get(url, headers=self._headers(), params=params, timeout=30.0)
                if not resp.is_success:
                    logger.error("google calendar api error", status=resp.status_code, body=resp.text[:500])
                resp.raise_for_status()
                data = resp.json()

                for item in data.get("items", []):
                    normalized = _normalize_google_event(item, calendar_id)
                    if normalized:
                        events.append(normalized)

                next_page = data.get("nextPageToken")
                if next_page:
                    params["pageToken"] = next_page
                    url = f"{GOOGLE_CALENDAR_API}/calendars/{calendar_id}/events"
                else:
                    url = ""  # type: ignore[assignment]

        logger.info("google calendar fetched", calendar_id=calendar_id, count=len(events))
        return events

    async def create_event(self, calendar_id: str, event_data: dict) -> dict:
        body = _to_google_event(event_data)
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{GOOGLE_CALENDAR_API}/calendars/{calendar_id}/events",
                headers=self._headers(),
                json=body,
                timeout=30.0,
            )
            resp.raise_for_status()
            item = resp.json()
        return _normalize_google_event(item, calendar_id) or {}

    async def update_event(self, calendar_id: str, event_id: str, event_data: dict) -> dict:
        body = _to_google_event(event_data)
        async with httpx.AsyncClient() as client:
            resp = await client.patch(
                f"{GOOGLE_CALENDAR_API}/calendars/{calendar_id}/events/{event_id}",
                headers=self._headers(),
                json=body,
                timeout=30.0,
            )
            resp.raise_for_status()
            item = resp.json()
        return _normalize_google_event(item, calendar_id) or {}


def _normalize_google_event(item: dict, calendar_id: str) -> dict | None:
    """Convert a Google Calendar event to our normalized format."""
    try:
        start = item.get("start", {})
        end = item.get("end", {})
        all_day = "date" in start

        if all_day:
            start_at = datetime.fromisoformat(start["date"]).replace(tzinfo=timezone.utc)
            end_at = datetime.fromisoformat(end["date"]).replace(tzinfo=timezone.utc)
        else:
            start_str = start.get("dateTime", "")
            end_str = end.get("dateTime", "")
            start_at = datetime.fromisoformat(start_str)
            end_at = datetime.fromisoformat(end_str)

        attendees = []
        for a in item.get("attendees", []):
            attendees.append({
                "email": a.get("email", ""),
                "name": a.get("displayName"),
                "status": a.get("responseStatus", "needsAction"),
            })

        return {
            "provider": "gmail",
            "external_id": item["id"],
            "calendar_id": calendar_id,
            "title": item.get("summary", "(No title)"),
            "description": item.get("description", ""),
            "start_at": start_at,
            "end_at": end_at,
            "all_day": all_day,
            "location": item.get("location", ""),
            "status": item.get("status", "confirmed"),
            "organizer": item.get("organizer", {}).get("email"),
            "attendees": attendees,
        }
    except (KeyError, ValueError):
        logger.warning("failed to parse google calendar event", event_id=item.get("id"))
        return None


def _to_google_event(data: dict) -> dict:
    """Convert our normalized event data to Google Calendar format."""
    body: dict = {}
    if "title" in data:
        body["summary"] = data["title"]
    if "description" in data:
        body["description"] = data["description"]
    if "location" in data:
        body["location"] = data["location"]
    if "start_at" in data:
        if data.get("all_day"):
            body["start"] = {"date": data["start_at"][:10]}
        else:
            body["start"] = {"dateTime": data["start_at"]}
    if "end_at" in data:
        if data.get("all_day"):
            body["end"] = {"date": data["end_at"][:10]}
        else:
            body["end"] = {"dateTime": data["end_at"]}
    return body
