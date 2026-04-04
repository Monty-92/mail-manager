"""Tests for BFF ingestion router."""

from unittest.mock import AsyncMock, patch

import httpx
import pytest


def _mock_response(status_code: int = 200, json_data: dict | list | None = None) -> httpx.Response:
    return httpx.Response(status_code=status_code, json=json_data if json_data is not None else {})


@pytest.mark.asyncio
async def test_get_auth_url(client):
    with patch("bff.routers.ingestion.get_client", new_callable=AsyncMock) as mock_get:
        mock_http = AsyncMock()
        mock_http.get.return_value = _mock_response(200, {"url": "https://accounts.google.com/auth"})
        mock_get.return_value = mock_http
        response = await client.get("/api/v1/ingest/auth/url/gmail")
    assert response.status_code == 200
    assert response.json()["url"] == "https://accounts.google.com/auth"


@pytest.mark.asyncio
async def test_get_auth_url_upstream_error(client):
    with patch("bff.routers.ingestion.get_client", new_callable=AsyncMock) as mock_get:
        mock_http = AsyncMock()
        mock_http.get.return_value = _mock_response(400, {"detail": "invalid provider"})
        mock_get.return_value = mock_http
        response = await client.get("/api/v1/ingest/auth/url/invalid")
    assert response.status_code == 400
    assert response.json()["detail"] == "invalid provider"


@pytest.mark.asyncio
async def test_auth_callback(client):
    with patch("bff.routers.ingestion.get_client", new_callable=AsyncMock) as mock_get:
        mock_http = AsyncMock()
        mock_http.post.return_value = _mock_response(200, {"status": "authenticated"})
        mock_get.return_value = mock_http
        response = await client.post("/api/v1/ingest/auth/callback", json={"code": "abc123"})
    assert response.status_code == 200
    assert response.json()["status"] == "authenticated"


@pytest.mark.asyncio
async def test_sync_provider(client):
    with patch("bff.routers.ingestion.get_client", new_callable=AsyncMock) as mock_get:
        mock_http = AsyncMock()
        mock_http.post.return_value = _mock_response(200, {"emails_synced": 5})
        mock_get.return_value = mock_http
        response = await client.post("/api/v1/ingest/sync/gmail?max_results=50")
    assert response.status_code == 200
    assert response.json()["emails_synced"] == 5


@pytest.mark.asyncio
async def test_fetch_provider(client):
    with patch("bff.routers.ingestion.get_client", new_callable=AsyncMock) as mock_get:
        mock_http = AsyncMock()
        mock_http.post.return_value = _mock_response(200, {"emails_fetched": 100})
        mock_get.return_value = mock_http
        response = await client.post("/api/v1/ingest/fetch/gmail")
    assert response.status_code == 200
    assert response.json()["emails_fetched"] == 100


@pytest.mark.asyncio
async def test_fetch_provider_with_page_token(client):
    with patch("bff.routers.ingestion.get_client", new_callable=AsyncMock) as mock_get:
        mock_http = AsyncMock()
        mock_http.post.return_value = _mock_response(200, {"emails_fetched": 50})
        mock_get.return_value = mock_http
        response = await client.post("/api/v1/ingest/fetch/outlook?page_token=abc")
    assert response.status_code == 200
