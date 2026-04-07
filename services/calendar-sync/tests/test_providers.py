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
