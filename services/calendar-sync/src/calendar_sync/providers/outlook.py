"""Microsoft Graph Calendar API provider."""

from datetime import datetime, timezone

import httpx
import structlog

from calendar_sync.providers import BaseCalendarProvider

logger = structlog.get_logger()

GRAPH_BASE = "https://graph.microsoft.com/v1.0"


class OutlookCalendarProvider(BaseCalendarProvider):
    def __init__(self, access_token: str) -> None:
        self._access_token = access_token

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._access_token}", "Content-Type": "application/json"}

    async def fetch_events(
        self, calendar_id: str = "primary", time_min: datetime | None = None, time_max: datetime | None = None
    ) -> list[dict]:
        params: dict[str, str] = {"$top": "250", "$orderby": "start/dateTime"}
        if time_min:
            params["$filter"] = f"end/dateTime ge '{time_min.isoformat()}'"
            if time_max:
                params["$filter"] += f" and start/dateTime le '{time_max.isoformat()}'"
        elif time_max:
            params["$filter"] = f"start/dateTime le '{time_max.isoformat()}'"

        events: list[dict] = []
        url = f"{GRAPH_BASE}/me/events"

        async with httpx.AsyncClient() as client:
            while url:
                resp = await client.get(url, headers=self._headers(), params=params, timeout=30.0)
                resp.raise_for_status()
                data = resp.json()

                for item in data.get("value", []):
                    normalized = _normalize_outlook_event(item, calendar_id)
                    if normalized:
                        events.append(normalized)

                url = data.get("@odata.nextLink", "")
                params = {}  # nextLink already includes params

        logger.info("outlook calendar fetched", count=len(events))
        return events

    async def create_event(self, calendar_id: str, event_data: dict) -> dict:
        body = _to_graph_event(event_data)
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{GRAPH_BASE}/me/events",
                headers=self._headers(),
                json=body,
                timeout=30.0,
            )
            resp.raise_for_status()
            item = resp.json()
        return _normalize_outlook_event(item, calendar_id) or {}

    async def update_event(self, calendar_id: str, event_id: str, event_data: dict) -> dict:
        body = _to_graph_event(event_data)
        async with httpx.AsyncClient() as client:
            resp = await client.patch(
                f"{GRAPH_BASE}/me/events/{event_id}",
                headers=self._headers(),
                json=body,
                timeout=30.0,
            )
            resp.raise_for_status()
            item = resp.json()
        return _normalize_outlook_event(item, calendar_id) or {}


def _normalize_outlook_event(item: dict, calendar_id: str) -> dict | None:
    """Convert a Graph Calendar event to our normalized format."""
    try:
        start_data = item.get("start", {})
        end_data = item.get("end", {})
        all_day = item.get("isAllDay", False)

        start_str = start_data.get("dateTime", "")
        end_str = end_data.get("dateTime", "")

        # Graph returns datetimes without timezone, defaulting to the event's timezone
        start_at = datetime.fromisoformat(start_str).replace(tzinfo=timezone.utc) if start_str else datetime.now(tz=timezone.utc)
        end_at = datetime.fromisoformat(end_str).replace(tzinfo=timezone.utc) if end_str else start_at

        attendees = []
        for a in item.get("attendees", []):
            ea = a.get("emailAddress", {})
            attendees.append({
                "email": ea.get("address", ""),
                "name": ea.get("name"),
                "status": a.get("status", {}).get("response", "none"),
            })

        organizer_data = item.get("organizer", {}).get("emailAddress", {})

        status_map = {"accepted": "confirmed", "tentativelyAccepted": "tentative", "declined": "cancelled"}
        raw_status = item.get("showAs", "busy")

        return {
            "provider": "outlook",
            "external_id": item["id"],
            "calendar_id": calendar_id,
            "title": item.get("subject", "(No title)"),
            "description": item.get("bodyPreview", ""),
            "start_at": start_at,
            "end_at": end_at,
            "all_day": all_day,
            "location": item.get("location", {}).get("displayName", ""),
            "status": "confirmed",
            "organizer": organizer_data.get("address"),
            "attendees": attendees,
        }
    except (KeyError, ValueError):
        logger.warning("failed to parse outlook calendar event", event_id=item.get("id"))
        return None


def _to_graph_event(data: dict) -> dict:
    """Convert our normalized event data to Microsoft Graph format."""
    body: dict = {}
    if "title" in data:
        body["subject"] = data["title"]
    if "description" in data:
        body["body"] = {"contentType": "text", "content": data["description"]}
    if "location" in data:
        body["location"] = {"displayName": data["location"]}
    if "start_at" in data:
        body["start"] = {"dateTime": data["start_at"], "timeZone": "UTC"}
    if "end_at" in data:
        body["end"] = {"dateTime": data["end_at"], "timeZone": "UTC"}
    if "all_day" in data:
        body["isAllDay"] = data["all_day"]
    return body
