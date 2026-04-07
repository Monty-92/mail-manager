"""Tests for the calendar-sync router."""

import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest


def _make_event(**kwargs) -> dict:
    """Build a minimal event dict matching _event_to_response expectations."""
    now = datetime.now(tz=timezone.utc)
    defaults = {
        "id": uuid4(),
        "provider": "gmail",
        "external_id": "ext-1",
        "calendar_id": str(uuid4()),
        "title": "Stand-up",
        "description": "",
        "start_at": now,
        "end_at": now,
        "all_day": False,
        "location": "",
        "status": "confirmed",
        "organizer": None,
        "attendees": [],
        "created_at": now,
        "updated_at": now,
    }
    defaults.update(kwargs)
    return defaults


class TestListEvents:
    @pytest.mark.asyncio
    async def test_returns_empty_list(self, client) -> None:
        with patch("calendar_sync.router.get_events", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = []
            response = await client.get("/calendar/events")
        assert response.status_code == 200
        assert response.json() == []

    @pytest.mark.asyncio
    async def test_returns_events(self, client) -> None:
        event = _make_event()
        with patch("calendar_sync.router.get_events", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = [event]
            response = await client.get("/calendar/events")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["title"] == "Stand-up"
        assert data[0]["provider"] == "gmail"

    @pytest.mark.asyncio
    async def test_passes_provider_and_limit_to_repository(self, client) -> None:
        with patch("calendar_sync.router.get_events", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = []
            await client.get("/calendar/events", params={"provider": "gmail", "limit": 50})
        mock_get.assert_called_once()
        kwargs = mock_get.call_args.kwargs
        assert kwargs["provider"] == "gmail"
        assert kwargs["limit"] == 50

    @pytest.mark.asyncio
    async def test_passes_date_filters_to_repository(self, client) -> None:
        with patch("calendar_sync.router.get_events", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = []
            await client.get(
                "/calendar/events",
                params={"start_after": "2026-04-01T00:00:00", "end_before": "2026-04-30T23:59:59"},
            )
        kwargs = mock_get.call_args.kwargs
        assert kwargs["start_after"] is not None
        assert kwargs["end_before"] is not None

    @pytest.mark.asyncio
    async def test_attendees_stored_as_json_string_are_parsed(self, client) -> None:
        """attendees stored as a JSON string (from DB) should be deserialized to a list."""
        attendees = [{"email": "bob@example.com", "name": "Bob", "status": "accepted"}]
        event = _make_event(attendees=json.dumps(attendees))
        with patch("calendar_sync.router.get_events", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = [event]
            response = await client.get("/calendar/events")
        assert response.status_code == 200
        assert response.json()[0]["attendees"][0]["email"] == "bob@example.com"

    @pytest.mark.asyncio
    async def test_multiple_events_returned(self, client) -> None:
        events = [_make_event(title="Meeting A"), _make_event(title="Meeting B")]
        with patch("calendar_sync.router.get_events", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = events
            response = await client.get("/calendar/events")
        assert response.status_code == 200
        titles = [e["title"] for e in response.json()]
        assert "Meeting A" in titles
        assert "Meeting B" in titles


class TestListSources:
    @pytest.mark.asyncio
    async def test_returns_calendars_grouped_by_account(self, client) -> None:
        account_id = uuid4()
        calendars = [
            {
                "account_id": account_id,
                "provider": "gmail",
                "account_email": "user@gmail.com",
                "account_name": "User",
                "id": uuid4(),
                "external_id": "primary",
                "name": "Primary",
                "color": "#4285f4",
                "is_primary": True,
                "enabled": True,
            }
        ]
        with patch("calendar_sync.router.get_all_calendars", new_callable=AsyncMock) as mock_all:
            mock_all.return_value = calendars
            response = await client.get("/calendar/sources")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["account_email"] == "user@gmail.com"
        assert len(data[0]["calendars"]) == 1
        assert data[0]["calendars"][0]["name"] == "Primary"
        assert data[0]["calendars"][0]["is_primary"] is True

    @pytest.mark.asyncio
    async def test_multiple_calendars_same_account_grouped_together(self, client) -> None:
        account_id = uuid4()
        cal_base = {
            "account_id": account_id,
            "provider": "gmail",
            "account_email": "user@gmail.com",
            "account_name": "User",
        }
        calendars = [
            {**cal_base, "id": uuid4(), "external_id": "primary", "name": "Primary", "color": "#4285f4", "is_primary": True, "enabled": True},
            {**cal_base, "id": uuid4(), "external_id": "work@cal", "name": "Work", "color": "#7986cb", "is_primary": False, "enabled": True},
        ]
        with patch("calendar_sync.router.get_all_calendars", new_callable=AsyncMock) as mock_all:
            mock_all.return_value = calendars
            response = await client.get("/calendar/sources")
        data = response.json()
        assert len(data) == 1  # single account
        assert len(data[0]["calendars"]) == 2

    @pytest.mark.asyncio
    async def test_fallback_to_accounts_when_no_calendars_synced(self, client) -> None:
        accounts = [
            {"id": uuid4(), "provider": "gmail", "email": "user@gmail.com", "display_name": "User"}
        ]
        with patch("calendar_sync.router.get_all_calendars", new_callable=AsyncMock) as mock_all:
            with patch("calendar_sync.router.get_calendar_accounts", new_callable=AsyncMock) as mock_accts:
                mock_all.return_value = []
                mock_accts.return_value = accounts
                response = await client.get("/calendar/sources")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["calendars"] == []
        assert data[0]["account_email"] == "user@gmail.com"

    @pytest.mark.asyncio
    async def test_empty_accounts_returns_empty_list(self, client) -> None:
        with patch("calendar_sync.router.get_all_calendars", new_callable=AsyncMock) as mock_all:
            with patch("calendar_sync.router.get_calendar_accounts", new_callable=AsyncMock) as mock_accts:
                mock_all.return_value = []
                mock_accts.return_value = []
                response = await client.get("/calendar/sources")
        assert response.status_code == 200
        assert response.json() == []


class TestSyncCalendar:
    @pytest.mark.asyncio
    async def test_no_accounts_returns_404(self, client) -> None:
        with patch("calendar_sync.router.get_calendar_accounts", new_callable=AsyncMock) as mock_accts:
            mock_accts.return_value = []
            response = await client.post("/calendar/sync", json={})
        assert response.status_code == 404
        assert "No calendar accounts" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_specific_account_not_found_returns_404(self, client) -> None:
        with patch("calendar_sync.router.get_calendar_account", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = None
            response = await client.post("/calendar/sync", json={"account_id": str(uuid4())})
        assert response.status_code == 404
        assert "Account not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_unknown_provider_is_skipped(self, client) -> None:
        accounts = [
            {
                "id": uuid4(),
                "provider": "unknown_provider",
                "email": "x@example.com",
                "access_token": "tok",
                "refresh_token": None,
                "token_expiry": None,
            }
        ]
        with patch("calendar_sync.router.get_calendar_accounts", new_callable=AsyncMock) as mock_accts:
            mock_accts.return_value = accounts
            response = await client.post("/calendar/sync", json={})
        assert response.status_code == 200
        assert response.json() == []

    @pytest.mark.asyncio
    async def test_sync_gmail_account_success(self, client) -> None:
        account_id = uuid4()
        accounts = [
            {
                "id": account_id,
                "provider": "gmail",
                "email": "user@gmail.com",
                "access_token": "valid-token",
                "refresh_token": "refresh-tok",
                "token_expiry": datetime(2099, 1, 1, tzinfo=timezone.utc),
            }
        ]
        calendars_db = [{"id": uuid4(), "external_id": "primary", "name": "Primary", "enabled": True}]
        provider_calendars = [{"external_id": "primary", "name": "Primary", "color": "#4285f4", "is_primary": True}]

        with patch("calendar_sync.router.get_calendar_accounts", new_callable=AsyncMock, return_value=accounts):
            with patch("calendar_sync.router.GoogleCalendarProvider") as MockProvider:
                mock_instance = MagicMock()
                mock_instance.list_calendars = AsyncMock(return_value=provider_calendars)
                mock_instance.fetch_events = AsyncMock(return_value=[])
                MockProvider.return_value = mock_instance
                with patch("calendar_sync.router.upsert_calendar", new_callable=AsyncMock):
                    with patch("calendar_sync.router.delete_stale_calendars", new_callable=AsyncMock, return_value=0):
                        with patch("calendar_sync.router.get_calendars_for_account", new_callable=AsyncMock, return_value=calendars_db):
                            with patch("calendar_sync.router.upsert_calendar_event", new_callable=AsyncMock):
                                response = await client.post("/calendar/sync", json={})

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["provider"] == "gmail"
        assert data[0]["account_email"] == "user@gmail.com"
        assert data[0]["synced"] == 0

    @pytest.mark.asyncio
    async def test_sync_counts_upserted_events(self, client) -> None:
        account_id = uuid4()
        accounts = [
            {
                "id": account_id,
                "provider": "gmail",
                "email": "user@gmail.com",
                "access_token": "valid-token",
                "refresh_token": "refresh-tok",
                "token_expiry": datetime(2099, 1, 1, tzinfo=timezone.utc),
            }
        ]
        cal_id = uuid4()
        calendars_db = [{"id": cal_id, "external_id": "primary", "name": "Primary", "enabled": True}]
        provider_calendars = [{"external_id": "primary", "name": "Primary", "color": "#4285f4", "is_primary": True}]
        now = datetime.now(tz=timezone.utc)
        fake_events = [
            {
                "provider": "gmail",
                "external_id": f"evt-{i}",
                "calendar_id": "primary",
                "title": f"Event {i}",
                "description": "",
                "start_at": now,
                "end_at": now,
                "all_day": False,
                "location": "",
                "status": "confirmed",
                "organizer": None,
                "attendees": [],
            }
            for i in range(3)
        ]

        with patch("calendar_sync.router.get_calendar_accounts", new_callable=AsyncMock, return_value=accounts):
            with patch("calendar_sync.router.GoogleCalendarProvider") as MockProvider:
                mock_instance = MagicMock()
                mock_instance.list_calendars = AsyncMock(return_value=provider_calendars)
                mock_instance.fetch_events = AsyncMock(return_value=fake_events)
                MockProvider.return_value = mock_instance
                with patch("calendar_sync.router.upsert_calendar", new_callable=AsyncMock):
                    with patch("calendar_sync.router.delete_stale_calendars", new_callable=AsyncMock, return_value=0):
                        with patch("calendar_sync.router.get_calendars_for_account", new_callable=AsyncMock, return_value=calendars_db):
                            with patch("calendar_sync.router.upsert_calendar_event", new_callable=AsyncMock):
                                response = await client.post("/calendar/sync", json={})

        assert response.json()[0]["synced"] == 3

    @pytest.mark.asyncio
    async def test_calendar_discovery_failure_falls_back_to_primary(self, client) -> None:
        account_id = uuid4()
        accounts = [
            {
                "id": account_id,
                "provider": "gmail",
                "email": "user@gmail.com",
                "access_token": "valid-token",
                "refresh_token": "refresh-tok",
                "token_expiry": datetime(2099, 1, 1, tzinfo=timezone.utc),
            }
        ]
        calendars_db = [{"id": uuid4(), "external_id": "primary", "name": "Primary", "enabled": True}]

        with patch("calendar_sync.router.get_calendar_accounts", new_callable=AsyncMock, return_value=accounts):
            with patch("calendar_sync.router.GoogleCalendarProvider") as MockProvider:
                mock_instance = MagicMock()
                mock_instance.list_calendars = AsyncMock(side_effect=Exception("API error"))
                mock_instance.fetch_events = AsyncMock(return_value=[])
                MockProvider.return_value = mock_instance
                with patch("calendar_sync.router.upsert_calendar", new_callable=AsyncMock) as mock_upsert:
                    with patch("calendar_sync.router.delete_stale_calendars", new_callable=AsyncMock, return_value=0):
                        with patch("calendar_sync.router.get_calendars_for_account", new_callable=AsyncMock, return_value=calendars_db):
                            with patch("calendar_sync.router.upsert_calendar_event", new_callable=AsyncMock):
                                response = await client.post("/calendar/sync", json={})

        assert response.status_code == 200
        # Fallback "Primary" calendar should have been upserted
        mock_upsert.assert_called_once()
        call_kwargs = mock_upsert.call_args.kwargs
        assert call_kwargs["external_id"] == "primary"

    @pytest.mark.asyncio
    async def test_sync_specific_account(self, client) -> None:
        account_id = uuid4()
        acct = {
            "id": account_id,
            "provider": "gmail",
            "email": "user@gmail.com",
            "access_token": "valid-token",
            "refresh_token": "refresh-tok",
            "token_expiry": datetime(2099, 1, 1, tzinfo=timezone.utc),
        }
        provider_calendars = [{"external_id": "primary", "name": "Primary", "color": "#4285f4", "is_primary": True}]
        calendars_db = [{"id": uuid4(), "external_id": "primary", "name": "Primary", "enabled": True}]

        with patch("calendar_sync.router.get_calendar_account", new_callable=AsyncMock, return_value=acct):
            with patch("calendar_sync.router.GoogleCalendarProvider") as MockProvider:
                mock_instance = MagicMock()
                mock_instance.list_calendars = AsyncMock(return_value=provider_calendars)
                mock_instance.fetch_events = AsyncMock(return_value=[])
                MockProvider.return_value = mock_instance
                with patch("calendar_sync.router.upsert_calendar", new_callable=AsyncMock):
                    with patch("calendar_sync.router.delete_stale_calendars", new_callable=AsyncMock, return_value=0):
                        with patch("calendar_sync.router.get_calendars_for_account", new_callable=AsyncMock, return_value=calendars_db):
                            with patch("calendar_sync.router.upsert_calendar_event", new_callable=AsyncMock):
                                response = await client.post("/calendar/sync", json={"account_id": str(account_id)})

        assert response.status_code == 200
        assert response.json()[0]["account_email"] == "user@gmail.com"


class TestRemoveEvent:
    @pytest.mark.asyncio
    async def test_event_deleted_successfully(self, client) -> None:
        event_id = uuid4()
        with patch("calendar_sync.router.delete_event", new_callable=AsyncMock) as mock_del:
            mock_del.return_value = 1
            response = await client.delete(f"/calendar/events/{event_id}")
        assert response.status_code == 200
        assert response.json() == {"detail": "Event deleted"}

    @pytest.mark.asyncio
    async def test_event_not_found_returns_404(self, client) -> None:
        event_id = uuid4()
        with patch("calendar_sync.router.delete_event", new_callable=AsyncMock) as mock_del:
            mock_del.return_value = 0
            response = await client.delete(f"/calendar/events/{event_id}")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_event_returns_none_gives_404(self, client) -> None:
        event_id = uuid4()
        with patch("calendar_sync.router.delete_event", new_callable=AsyncMock) as mock_del:
            mock_del.return_value = None
            response = await client.delete(f"/calendar/events/{event_id}")
        assert response.status_code == 404


class TestRefreshGoogleToken:
    @pytest.mark.asyncio
    async def test_valid_future_expiry_returns_existing_token(self) -> None:
        """Token with expiry well in the future is returned without calling Google."""
        from calendar_sync.router import _refresh_google_token

        acct = {
            "id": uuid4(),
            "email": "user@gmail.com",
            "access_token": "existing-token",
            "refresh_token": "refresh-tok",
            "token_expiry": datetime(2099, 1, 1, tzinfo=timezone.utc),
        }
        result = await _refresh_google_token(acct)
        assert result == "existing-token"

    @pytest.mark.asyncio
    async def test_no_refresh_token_returns_existing_token(self) -> None:
        """No refresh token means we can only return the existing access token."""
        from calendar_sync.router import _refresh_google_token

        acct = {
            "id": uuid4(),
            "email": "user@gmail.com",
            "access_token": "existing-token",
            "refresh_token": None,
            "token_expiry": datetime(2020, 1, 1, tzinfo=timezone.utc),  # expired
        }
        result = await _refresh_google_token(acct)
        assert result == "existing-token"

    @pytest.mark.asyncio
    async def test_no_expiry_triggers_refresh(self) -> None:
        """token_expiry=None means expiry check is skipped; with refresh token, tries to refresh."""
        from calendar_sync.router import _refresh_google_token

        acct = {
            "id": uuid4(),
            "email": "user@gmail.com",
            "access_token": "old-token",
            "refresh_token": "refresh-tok",
            "token_expiry": None,
        }
        mock_creds = MagicMock()
        mock_creds.token = "new-token"
        mock_creds.expiry = datetime(2099, 1, 1)

        with patch("calendar_sync.router.Credentials") as mock_creds_cls:
            mock_creds_cls.return_value = mock_creds
            with patch("calendar_sync.router.Request"):
                with patch("calendar_sync.router.update_account_token", new_callable=AsyncMock):
                    result = await _refresh_google_token(acct)

        assert result == "new-token"
        mock_creds.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_expired_token_refreshed(self) -> None:
        """Expired token with valid refresh token calls Google and returns new token."""
        from calendar_sync.router import _refresh_google_token

        acct = {
            "id": uuid4(),
            "email": "user@gmail.com",
            "access_token": "old-token",
            "refresh_token": "refresh-tok",
            "token_expiry": datetime(2020, 1, 1, tzinfo=timezone.utc),  # expired
        }
        mock_creds = MagicMock()
        mock_creds.token = "new-token"
        mock_creds.expiry = datetime(2099, 1, 1)

        with patch("calendar_sync.router.Credentials") as mock_creds_cls:
            mock_creds_cls.return_value = mock_creds
            with patch("calendar_sync.router.Request"):
                with patch("calendar_sync.router.update_account_token", new_callable=AsyncMock) as mock_update:
                    result = await _refresh_google_token(acct)

        assert result == "new-token"
        mock_creds.refresh.assert_called_once()
        mock_update.assert_called_once()
