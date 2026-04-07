"""Tests for BFF accounts router (proxy to ingestion service)."""

from unittest.mock import AsyncMock, patch
from uuid import uuid4

import httpx
import pytest


def _mock_response(status_code: int = 200, json_data: dict | list | None = None) -> httpx.Response:
    return httpx.Response(status_code=status_code, json=json_data if json_data is not None else {})


class TestListAccounts:
    @pytest.mark.asyncio
    async def test_returns_connected_accounts(self, client) -> None:
        accounts = [
            {"id": str(uuid4()), "provider": "gmail", "email": "user@gmail.com"},
        ]
        with patch("bff.routers.accounts.get_client", new_callable=AsyncMock) as mock_get:
            mock_http = AsyncMock()
            mock_http.get.return_value = _mock_response(200, accounts)
            mock_get.return_value = mock_http
            response = await client.get("/api/v1/accounts")
        assert response.status_code == 200
        assert len(response.json()) == 1
        assert response.json()[0]["provider"] == "gmail"

    @pytest.mark.asyncio
    async def test_returns_empty_list_when_none_connected(self, client) -> None:
        with patch("bff.routers.accounts.get_client", new_callable=AsyncMock) as mock_get:
            mock_http = AsyncMock()
            mock_http.get.return_value = _mock_response(200, [])
            mock_get.return_value = mock_http
            response = await client.get("/api/v1/accounts")
        assert response.status_code == 200
        assert response.json() == []

    @pytest.mark.asyncio
    async def test_upstream_error_propagated(self, client) -> None:
        with patch("bff.routers.accounts.get_client", new_callable=AsyncMock) as mock_get:
            mock_http = AsyncMock()
            mock_http.get.return_value = _mock_response(500, {"detail": "internal error"})
            mock_get.return_value = mock_http
            response = await client.get("/api/v1/accounts")
        assert response.status_code == 500


class TestDisconnectAccount:
    @pytest.mark.asyncio
    async def test_disconnects_successfully(self, client) -> None:
        account_id = uuid4()
        with patch("bff.routers.accounts.get_client", new_callable=AsyncMock) as mock_get:
            mock_http = AsyncMock()
            mock_http.delete.return_value = _mock_response(200, {"detail": "Account disconnected"})
            mock_get.return_value = mock_http
            response = await client.delete(f"/api/v1/accounts/{account_id}")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_account_not_found_propagated(self, client) -> None:
        account_id = uuid4()
        with patch("bff.routers.accounts.get_client", new_callable=AsyncMock) as mock_get:
            mock_http = AsyncMock()
            mock_http.delete.return_value = _mock_response(404, {"detail": "Account not found"})
            mock_get.return_value = mock_http
            response = await client.delete(f"/api/v1/accounts/{account_id}")
        assert response.status_code == 404


class TestGetAuthUrl:
    @pytest.mark.asyncio
    async def test_returns_auth_url_for_gmail(self, client) -> None:
        with patch("bff.routers.accounts.get_client", new_callable=AsyncMock) as mock_get:
            mock_http = AsyncMock()
            mock_http.get.return_value = _mock_response(200, {"url": "https://accounts.google.com/o/oauth2/auth?client_id=..."})
            mock_get.return_value = mock_http
            response = await client.get("/api/v1/accounts/auth/url/gmail")
        assert response.status_code == 200
        assert "url" in response.json()

    @pytest.mark.asyncio
    async def test_returns_auth_url_for_outlook(self, client) -> None:
        with patch("bff.routers.accounts.get_client", new_callable=AsyncMock) as mock_get:
            mock_http = AsyncMock()
            mock_http.get.return_value = _mock_response(200, {"url": "https://login.microsoftonline.com/common/oauth2/v2.0/authorize?..."})
            mock_get.return_value = mock_http
            response = await client.get("/api/v1/accounts/auth/url/outlook")
        assert response.status_code == 200
        assert "url" in response.json()

    @pytest.mark.asyncio
    async def test_unknown_provider_propagates_upstream_error(self, client) -> None:
        with patch("bff.routers.accounts.get_client", new_callable=AsyncMock) as mock_get:
            mock_http = AsyncMock()
            mock_http.get.return_value = _mock_response(400, {"detail": "Unknown provider"})
            mock_get.return_value = mock_http
            response = await client.get("/api/v1/accounts/auth/url/unknown")
        assert response.status_code == 400


class TestAuthCallback:
    @pytest.mark.asyncio
    async def test_successful_callback(self, client) -> None:
        connected = {"provider": "gmail", "email": "user@gmail.com", "id": str(uuid4())}
        with patch("bff.routers.accounts.get_client", new_callable=AsyncMock) as mock_get:
            mock_http = AsyncMock()
            mock_http.post.return_value = _mock_response(200, connected)
            mock_get.return_value = mock_http
            response = await client.post(
                "/api/v1/accounts/auth/callback",
                json={"code": "auth-code-123", "provider": "gmail", "state": "state-xyz"},
            )
        assert response.status_code == 200
        assert response.json()["provider"] == "gmail"

    @pytest.mark.asyncio
    async def test_invalid_code_propagates_error(self, client) -> None:
        with patch("bff.routers.accounts.get_client", new_callable=AsyncMock) as mock_get:
            mock_http = AsyncMock()
            mock_http.post.return_value = _mock_response(400, {"detail": "Invalid authorization code"})
            mock_get.return_value = mock_http
            response = await client.post("/api/v1/accounts/auth/callback", json={"code": "bad-code"})
        assert response.status_code == 400


class TestDeviceFlow:
    @pytest.mark.asyncio
    async def test_start_device_flow(self, client) -> None:
        device_response = {
            "device_code": "dev-code-abc",
            "user_code": "XXXX-YYYY",
            "verification_uri": "https://microsoft.com/devicelogin",
            "expires_in": 900,
        }
        with patch("bff.routers.accounts.get_client", new_callable=AsyncMock) as mock_get:
            mock_http = AsyncMock()
            mock_http.post.return_value = _mock_response(200, device_response)
            mock_get.return_value = mock_http
            response = await client.post("/api/v1/accounts/auth/device/outlook")
        assert response.status_code == 200
        assert "device_code" in response.json()
        assert "user_code" in response.json()

    @pytest.mark.asyncio
    async def test_poll_device_flow_pending(self, client) -> None:
        with patch("bff.routers.accounts.get_client", new_callable=AsyncMock) as mock_get:
            mock_http = AsyncMock()
            mock_http.post.return_value = _mock_response(200, {"status": "pending"})
            mock_get.return_value = mock_http
            response = await client.post(
                "/api/v1/accounts/auth/device/outlook/poll",
                params={"device_code": "dev-code-abc"},
            )
        assert response.status_code == 200
        assert response.json()["status"] == "pending"

    @pytest.mark.asyncio
    async def test_poll_device_flow_complete(self, client) -> None:
        connected = {"provider": "outlook", "email": "user@outlook.com", "id": str(uuid4())}
        with patch("bff.routers.accounts.get_client", new_callable=AsyncMock) as mock_get:
            mock_http = AsyncMock()
            mock_http.post.return_value = _mock_response(200, connected)
            mock_get.return_value = mock_http
            response = await client.post(
                "/api/v1/accounts/auth/device/outlook/poll",
                params={"device_code": "dev-code-abc"},
            )
        assert response.status_code == 200
        assert response.json()["provider"] == "outlook"
