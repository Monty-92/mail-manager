"""Tests for calendar provider list_calendars and Outlook color mapping."""

import pytest

from calendar_sync.providers.outlook import OutlookCalendarProvider, _outlook_color_to_hex


class TestOutlookColorMapping:
    def test_known_color(self) -> None:
        assert _outlook_color_to_hex("lightBlue") == "#71afe5"
        assert _outlook_color_to_hex("lightGreen") == "#7ed321"
        assert _outlook_color_to_hex("lightRed") == "#e74856"

    def test_auto_color(self) -> None:
        assert _outlook_color_to_hex("auto") == "#0078d4"

    def test_unknown_color_defaults(self) -> None:
        assert _outlook_color_to_hex("someNewColor") == "#0078d4"

    def test_empty_string_defaults(self) -> None:
        assert _outlook_color_to_hex("") == "#0078d4"


class TestGoogleListCalendars:
    @pytest.mark.asyncio
    async def test_list_calendars_parses_response(self) -> None:
        """GoogleCalendarProvider.list_calendars should parse calendarList items."""
        from unittest.mock import AsyncMock, MagicMock, patch

        from calendar_sync.providers.google import GoogleCalendarProvider

        fake_response = MagicMock()
        fake_response.raise_for_status = MagicMock()
        fake_response.json.return_value = {
            "items": [
                {"id": "primary@gmail.com", "summary": "Primary", "backgroundColor": "#4285f4", "primary": True},
                {"id": "work@gmail.com", "summary": "Work", "backgroundColor": "#7986cb"},
                {"id": "holidays@group.v.calendar.google.com", "summary": "Holidays", "backgroundColor": "#009688"},
            ],
        }

        with patch("calendar_sync.providers.google.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.get.return_value = fake_response
            mock_client_cls.return_value = mock_client

            provider = GoogleCalendarProvider(access_token="fake-token")
            calendars = await provider.list_calendars()

        assert len(calendars) == 3
        assert calendars[0]["external_id"] == "primary@gmail.com"
        assert calendars[0]["name"] == "Primary"
        assert calendars[0]["is_primary"] is True
        assert calendars[1]["name"] == "Work"
        assert calendars[1]["is_primary"] is False
        assert calendars[2]["color"] == "#009688"

    @pytest.mark.asyncio
    async def test_list_calendars_pagination(self) -> None:
        """GoogleCalendarProvider.list_calendars paginates using nextPageToken."""
        from unittest.mock import AsyncMock, MagicMock, patch

        from calendar_sync.providers.google import GoogleCalendarProvider

        page1 = MagicMock()
        page1.raise_for_status = MagicMock()
        page1.json.return_value = {
            "items": [{"id": "cal-1", "summary": "Cal 1"}],
            "nextPageToken": "page2token",
        }
        page2 = MagicMock()
        page2.raise_for_status = MagicMock()
        page2.json.return_value = {
            "items": [{"id": "cal-2", "summary": "Cal 2"}],
        }

        with patch("calendar_sync.providers.google.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.get.side_effect = [page1, page2]
            mock_client_cls.return_value = mock_client

            provider = GoogleCalendarProvider(access_token="fake-token")
            calendars = await provider.list_calendars()

        assert len(calendars) == 2
        assert calendars[0]["external_id"] == "cal-1"
        assert calendars[1]["external_id"] == "cal-2"


class TestOutlookListCalendars:
    @pytest.mark.asyncio
    async def test_list_calendars_parses_response(self) -> None:
        """OutlookCalendarProvider.list_calendars should parse Graph calendars response."""
        from unittest.mock import AsyncMock, MagicMock, patch

        fake_response = MagicMock()
        fake_response.raise_for_status = MagicMock()
        fake_response.json.return_value = {
            "value": [
                {"id": "cal-id-1", "name": "Calendar", "color": "auto", "isDefaultCalendar": True},
                {"id": "cal-id-2", "name": "Birthdays", "color": "lightPink", "isDefaultCalendar": False},
            ],
        }

        with patch("calendar_sync.providers.outlook.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.get.return_value = fake_response
            mock_client_cls.return_value = mock_client

            provider = OutlookCalendarProvider(access_token="fake-token")
            calendars = await provider.list_calendars()

        assert len(calendars) == 2
        assert calendars[0]["external_id"] == "cal-id-1"
        assert calendars[0]["name"] == "Calendar"
        assert calendars[0]["is_primary"] is True
        assert calendars[0]["color"] == "#0078d4"  # "auto" mapped
        assert calendars[1]["name"] == "Birthdays"
        assert calendars[1]["color"] == "#e3008c"  # "lightPink" mapped
        assert calendars[1]["is_primary"] is False


class TestGoogleEventNormalization:
    def test_timed_event(self) -> None:
        from calendar_sync.providers.google import _normalize_google_event

        item = {
            "id": "event-1",
            "summary": "Team Sync",
            "description": "Weekly meeting",
            "start": {"dateTime": "2026-04-08T10:00:00+01:00"},
            "end": {"dateTime": "2026-04-08T11:00:00+01:00"},
            "location": "Zoom",
            "status": "confirmed",
        }
        result = _normalize_google_event(item, "primary")
        assert result is not None
        assert result["provider"] == "gmail"
        assert result["title"] == "Team Sync"
        assert result["description"] == "Weekly meeting"
        assert result["all_day"] is False
        assert result["calendar_id"] == "primary"
        assert result["external_id"] == "event-1"

    def test_all_day_event(self) -> None:
        from calendar_sync.providers.google import _normalize_google_event

        item = {
            "id": "event-2",
            "summary": "Holiday",
            "start": {"date": "2026-04-08"},
            "end": {"date": "2026-04-09"},
            "status": "confirmed",
        }
        result = _normalize_google_event(item, "primary")
        assert result is not None
        assert result["all_day"] is True
        assert result["title"] == "Holiday"

    def test_event_with_attendees(self) -> None:
        from calendar_sync.providers.google import _normalize_google_event

        item = {
            "id": "event-3",
            "summary": "Meeting",
            "start": {"dateTime": "2026-04-08T10:00:00Z"},
            "end": {"dateTime": "2026-04-08T11:00:00Z"},
            "attendees": [
                {"email": "alice@example.com", "displayName": "Alice", "responseStatus": "accepted"},
                {"email": "bob@example.com", "responseStatus": "needsAction"},
            ],
            "organizer": {"email": "alice@example.com"},
        }
        result = _normalize_google_event(item, "cal-1")
        assert result is not None
        assert len(result["attendees"]) == 2
        assert result["attendees"][0]["name"] == "Alice"
        assert result["attendees"][0]["status"] == "accepted"
        assert result["attendees"][1]["email"] == "bob@example.com"
        assert result["attendees"][1]["status"] == "needsAction"
        assert result["organizer"] == "alice@example.com"

    def test_missing_required_field_returns_none(self) -> None:
        """Event dict without 'id' triggers KeyError → returns None."""
        from calendar_sync.providers.google import _normalize_google_event

        item = {
            "summary": "No ID event",
            "start": {"dateTime": "2026-04-08T10:00:00Z"},
            "end": {"dateTime": "2026-04-08T11:00:00Z"},
        }
        result = _normalize_google_event(item, "primary")
        assert result is None

    def test_default_title_when_no_summary(self) -> None:
        from calendar_sync.providers.google import _normalize_google_event

        item = {
            "id": "event-4",
            "start": {"dateTime": "2026-04-08T10:00:00Z"},
            "end": {"dateTime": "2026-04-08T11:00:00Z"},
        }
        result = _normalize_google_event(item, "primary")
        assert result is not None
        assert result["title"] == "(No title)"

    def test_invalid_datetime_string_returns_none(self) -> None:
        """Malformed dateTime string triggers ValueError → returns None."""
        from calendar_sync.providers.google import _normalize_google_event

        item = {
            "id": "event-5",
            "start": {"dateTime": "not-a-date"},
            "end": {"dateTime": "also-not-a-date"},
        }
        result = _normalize_google_event(item, "primary")
        assert result is None


class TestGoogleFetchEvents:
    @pytest.mark.asyncio
    async def test_fetch_events_returns_normalized_events(self) -> None:
        from unittest.mock import AsyncMock, MagicMock, patch

        from calendar_sync.providers.google import GoogleCalendarProvider

        item = {
            "id": "evt-1",
            "summary": "Stand-up",
            "start": {"dateTime": "2026-04-08T09:00:00Z"},
            "end": {"dateTime": "2026-04-08T09:30:00Z"},
            "status": "confirmed",
        }
        fake_response = MagicMock()
        fake_response.raise_for_status = MagicMock()
        fake_response.is_success = True
        fake_response.json.return_value = {"items": [item]}

        with patch("calendar_sync.providers.google.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.get.return_value = fake_response
            mock_client_cls.return_value = mock_client

            provider = GoogleCalendarProvider(access_token="fake-token")
            events = await provider.fetch_events(calendar_id="primary")

        assert len(events) == 1
        assert events[0]["title"] == "Stand-up"
        assert events[0]["provider"] == "gmail"
        assert events[0]["all_day"] is False

    @pytest.mark.asyncio
    async def test_fetch_events_skips_invalid_items(self) -> None:
        """Items that fail normalization (no 'id') should be silently skipped."""
        from unittest.mock import AsyncMock, MagicMock, patch

        from calendar_sync.providers.google import GoogleCalendarProvider

        bad_item = {
            "summary": "No ID",
            "start": {"dateTime": "2026-04-08T09:00:00Z"},
            "end": {"dateTime": "2026-04-08T10:00:00Z"},
        }
        good_item = {
            "id": "valid-evt",
            "summary": "Valid",
            "start": {"dateTime": "2026-04-08T10:00:00Z"},
            "end": {"dateTime": "2026-04-08T11:00:00Z"},
        }
        fake_response = MagicMock()
        fake_response.raise_for_status = MagicMock()
        fake_response.is_success = True
        fake_response.json.return_value = {"items": [bad_item, good_item]}

        with patch("calendar_sync.providers.google.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.get.return_value = fake_response
            mock_client_cls.return_value = mock_client

            provider = GoogleCalendarProvider(access_token="fake-token")
            events = await provider.fetch_events(calendar_id="primary")

        assert len(events) == 1
        assert events[0]["external_id"] == "valid-evt"

    @pytest.mark.asyncio
    async def test_fetch_events_empty_response(self) -> None:
        from unittest.mock import AsyncMock, MagicMock, patch

        from calendar_sync.providers.google import GoogleCalendarProvider

        fake_response = MagicMock()
        fake_response.raise_for_status = MagicMock()
        fake_response.is_success = True
        fake_response.json.return_value = {"items": []}

        with patch("calendar_sync.providers.google.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.get.return_value = fake_response
            mock_client_cls.return_value = mock_client

            provider = GoogleCalendarProvider(access_token="fake-token")
            events = await provider.fetch_events(calendar_id="primary")

        assert events == []

    @pytest.mark.asyncio
    async def test_fetch_events_pagination(self) -> None:
        """fetch_events follows nextPageToken pagination."""
        from unittest.mock import AsyncMock, MagicMock, patch

        from calendar_sync.providers.google import GoogleCalendarProvider

        def _make_item(evt_id: str) -> dict:
            return {
                "id": evt_id,
                "summary": f"Event {evt_id}",
                "start": {"dateTime": "2026-04-08T10:00:00Z"},
                "end": {"dateTime": "2026-04-08T11:00:00Z"},
            }

        page1 = MagicMock()
        page1.raise_for_status = MagicMock()
        page1.is_success = True
        page1.json.return_value = {"items": [_make_item("evt-1")], "nextPageToken": "page2token"}

        page2 = MagicMock()
        page2.raise_for_status = MagicMock()
        page2.is_success = True
        page2.json.return_value = {"items": [_make_item("evt-2")]}

        with patch("calendar_sync.providers.google.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.get.side_effect = [page1, page2]
            mock_client_cls.return_value = mock_client

            provider = GoogleCalendarProvider(access_token="fake-token")
            events = await provider.fetch_events(calendar_id="primary")

        assert len(events) == 2
        assert {e["external_id"] for e in events} == {"evt-1", "evt-2"}


class TestOutlookFetchEventsCalendarId:
    @pytest.mark.asyncio
    async def test_specific_calendar_uses_calendar_url(self) -> None:
        """OutlookCalendarProvider.fetch_events with specific calendar_id uses /me/calendars/{id}/events."""
        from unittest.mock import AsyncMock, MagicMock, patch

        fake_response = MagicMock()
        fake_response.raise_for_status = MagicMock()
        fake_response.json.return_value = {"value": []}

        with patch("calendar_sync.providers.outlook.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.get.return_value = fake_response
            mock_client_cls.return_value = mock_client

            provider = OutlookCalendarProvider(access_token="fake-token")
            await provider.fetch_events(calendar_id="specific-cal-id")

        call_args = mock_client.get.call_args
        url = call_args.args[0] if call_args.args else call_args.kwargs.get("url", "")
        assert "calendars/specific-cal-id/events" in url

    @pytest.mark.asyncio
    async def test_primary_calendar_uses_me_events(self) -> None:
        """OutlookCalendarProvider.fetch_events with 'primary' uses /me/events."""
        from unittest.mock import AsyncMock, MagicMock, patch

        fake_response = MagicMock()
        fake_response.raise_for_status = MagicMock()
        fake_response.json.return_value = {"value": []}

        with patch("calendar_sync.providers.outlook.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.get.return_value = fake_response
            mock_client_cls.return_value = mock_client

            provider = OutlookCalendarProvider(access_token="fake-token")
            await provider.fetch_events(calendar_id="primary")

        call_args = mock_client.get.call_args
        url = call_args.args[0] if call_args.args else call_args.kwargs.get("url", "")
        assert url.endswith("/me/events")
