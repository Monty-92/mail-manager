"""Tests for BFF calendar router (proxy to calendar-sync service)."""

from unittest.mock import AsyncMock, patch
from uuid import uuid4

import httpx
import pytest


def _mock_response(status_code: int = 200, json_data: dict | list | None = None) -> httpx.Response:
    return httpx.Response(status_code=status_code, json=json_data if json_data is not None else {})


class TestListEvents:
    @pytest.mark.asyncio
    async def test_returns_events(self, client) -> None:
        events = [
            {
                "id": str(uuid4()),
                "title": "Stand-up",
                "provider": "gmail",
                "start_at": "2026-04-08T09:00:00+00:00",
                "end_at": "2026-04-08T09:30:00+00:00",
            }
        ]
        with patch("bff.routers.calendar.get_client", new_callable=AsyncMock) as mock_get:
            mock_http = AsyncMock()
            mock_http.get.return_value = _mock_response(200, events)
            mock_get.return_value = mock_http
            response = await client.get("/api/v1/calendar/events")
        assert response.status_code == 200
        assert len(response.json()) == 1
        assert response.json()[0]["title"] == "Stand-up"

    @pytest.mark.asyncio
    async def test_returns_empty_list(self, client) -> None:
        with patch("bff.routers.calendar.get_client", new_callable=AsyncMock) as mock_get:
            mock_http = AsyncMock()
            mock_http.get.return_value = _mock_response(200, [])
            mock_get.return_value = mock_http
            response = await client.get("/api/v1/calendar/events")
        assert response.status_code == 200
        assert response.json() == []

    @pytest.mark.asyncio
    async def test_forwards_query_params(self, client) -> None:
        with patch("bff.routers.calendar.get_client", new_callable=AsyncMock) as mock_get:
            mock_http = AsyncMock()
            mock_http.get.return_value = _mock_response(200, [])
            mock_get.return_value = mock_http
            response = await client.get(
                "/api/v1/calendar/events",
                params={"provider": "gmail", "limit": 50, "start_after": "2026-04-01T00:00:00"},
            )
        assert response.status_code == 200
        # Verify that the upstream call included our params
        call_kwargs = mock_http.get.call_args
        assert call_kwargs is not None

    @pytest.mark.asyncio
    async def test_upstream_error_propagated(self, client) -> None:
        with patch("bff.routers.calendar.get_client", new_callable=AsyncMock) as mock_get:
            mock_http = AsyncMock()
            mock_http.get.return_value = _mock_response(503, {"detail": "service unavailable"})
            mock_get.return_value = mock_http
            response = await client.get("/api/v1/calendar/events")
        assert response.status_code == 503


class TestListSources:
    @pytest.mark.asyncio
    async def test_returns_sources(self, client) -> None:
        sources = [
            {
                "id": str(uuid4()),
                "provider": "gmail",
                "account_email": "user@gmail.com",
                "account_name": "User",
                "calendars": [{"id": str(uuid4()), "name": "Primary", "color": "#4285f4", "is_primary": True, "enabled": True}],
            }
        ]
        with patch("bff.routers.calendar.get_client", new_callable=AsyncMock) as mock_get:
            mock_http = AsyncMock()
            mock_http.get.return_value = _mock_response(200, sources)
            mock_get.return_value = mock_http
            response = await client.get("/api/v1/calendar/sources")
        assert response.status_code == 200
        assert response.json()[0]["account_email"] == "user@gmail.com"
        assert len(response.json()[0]["calendars"]) == 1

    @pytest.mark.asyncio
    async def test_returns_empty_when_no_accounts(self, client) -> None:
        with patch("bff.routers.calendar.get_client", new_callable=AsyncMock) as mock_get:
            mock_http = AsyncMock()
            mock_http.get.return_value = _mock_response(200, [])
            mock_get.return_value = mock_http
            response = await client.get("/api/v1/calendar/sources")
        assert response.status_code == 200
        assert response.json() == []


class TestSyncCalendar:
    @pytest.mark.asyncio
    async def test_sync_returns_results(self, client) -> None:
        results = [{"synced": 5, "provider": "gmail", "account_email": "user@gmail.com"}]
        with patch("bff.routers.calendar.get_client", new_callable=AsyncMock) as mock_get:
            mock_http = AsyncMock()
            mock_http.post.return_value = _mock_response(200, results)
            mock_get.return_value = mock_http
            response = await client.post("/api/v1/calendar/sync", json={})
        assert response.status_code == 200
        assert response.json()[0]["synced"] == 5
        assert response.json()[0]["provider"] == "gmail"

    @pytest.mark.asyncio
    async def test_sync_with_account_id(self, client) -> None:
        account_id = str(uuid4())
        results = [{"synced": 2, "provider": "gmail", "account_email": "user@gmail.com"}]
        with patch("bff.routers.calendar.get_client", new_callable=AsyncMock) as mock_get:
            mock_http = AsyncMock()
            mock_http.post.return_value = _mock_response(200, results)
            mock_get.return_value = mock_http
            response = await client.post("/api/v1/calendar/sync", json={"account_id": account_id})
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_sync_no_accounts_returns_404(self, client) -> None:
        with patch("bff.routers.calendar.get_client", new_callable=AsyncMock) as mock_get:
            mock_http = AsyncMock()
            mock_http.post.return_value = _mock_response(404, {"detail": "No calendar accounts connected"})
            mock_get.return_value = mock_http
            response = await client.post("/api/v1/calendar/sync", json={})
        assert response.status_code == 404
        assert "No calendar accounts" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_sync_account_not_found_returns_404(self, client) -> None:
        with patch("bff.routers.calendar.get_client", new_callable=AsyncMock) as mock_get:
            mock_http = AsyncMock()
            mock_http.post.return_value = _mock_response(404, {"detail": "Account not found"})
            mock_get.return_value = mock_http
            response = await client.post("/api/v1/calendar/sync", json={"account_id": str(uuid4())})
        assert response.status_code == 404


class TestDeleteEvent:
    @pytest.mark.asyncio
    async def test_event_deleted_successfully(self, client) -> None:
        event_id = str(uuid4())
        with patch("bff.routers.calendar.get_client", new_callable=AsyncMock) as mock_get:
            mock_http = AsyncMock()
            mock_http.delete.return_value = _mock_response(200, {"detail": "Event deleted"})
            mock_get.return_value = mock_http
            response = await client.delete(f"/api/v1/calendar/events/{event_id}")
        assert response.status_code == 200
        assert response.json()["detail"] == "Event deleted"

    @pytest.mark.asyncio
    async def test_event_not_found_returns_404(self, client) -> None:
        event_id = str(uuid4())
        with patch("bff.routers.calendar.get_client", new_callable=AsyncMock) as mock_get:
            mock_http = AsyncMock()
            mock_http.delete.return_value = _mock_response(404, {"detail": "Event not found"})
            mock_get.return_value = mock_http
            response = await client.delete(f"/api/v1/calendar/events/{event_id}")
        assert response.status_code == 404
