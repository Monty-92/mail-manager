"""Tests for BFF analysis router."""

from unittest.mock import AsyncMock, patch

import httpx
import pytest


def _mock_response(status_code: int = 200, json_data: dict | list | None = None) -> httpx.Response:
    return httpx.Response(status_code=status_code, json=json_data if json_data is not None else {})


@pytest.mark.asyncio
async def test_get_analysis(client):
    with patch("bff.routers.analysis.get_client", new_callable=AsyncMock) as mock_get:
        mock_http = AsyncMock()
        mock_http.get.return_value = _mock_response(200, {"email_id": "e-1", "category": "work"})
        mock_get.return_value = mock_http
        response = await client.get("/api/v1/analyze/e-1")
    assert response.status_code == 200
    assert response.json()["category"] == "work"


@pytest.mark.asyncio
async def test_get_analysis_not_found(client):
    with patch("bff.routers.analysis.get_client", new_callable=AsyncMock) as mock_get:
        mock_http = AsyncMock()
        mock_http.get.return_value = _mock_response(404, {"detail": "analysis not found"})
        mock_get.return_value = mock_http
        response = await client.get("/api/v1/analyze/nonexistent")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_analyze_batch(client):
    with patch("bff.routers.analysis.get_client", new_callable=AsyncMock) as mock_get:
        mock_http = AsyncMock()
        mock_http.post.return_value = _mock_response(200, {"analyzed": 5})
        mock_get.return_value = mock_http
        response = await client.post("/api/v1/analyze/batch?limit=5")
    assert response.status_code == 200
    assert response.json()["analyzed"] == 5


@pytest.mark.asyncio
async def test_analyze_email(client):
    with patch("bff.routers.analysis.get_client", new_callable=AsyncMock) as mock_get:
        mock_http = AsyncMock()
        mock_http.post.return_value = _mock_response(200, {"email_id": "e-1", "category": "urgent"})
        mock_get.return_value = mock_http
        response = await client.post("/api/v1/analyze/e-1")
    assert response.status_code == 200
    assert response.json()["email_id"] == "e-1"


@pytest.mark.asyncio
async def test_analyze_email_upstream_error(client):
    with patch("bff.routers.analysis.get_client", new_callable=AsyncMock) as mock_get:
        mock_http = AsyncMock()
        mock_http.post.return_value = _mock_response(500, {"detail": "llm unavailable"})
        mock_get.return_value = mock_http
        response = await client.post("/api/v1/analyze/e-1")
    assert response.status_code == 500
