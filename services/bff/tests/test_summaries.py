"""Tests for BFF summaries router."""

from unittest.mock import AsyncMock, patch

import httpx
import pytest


def _mock_response(status_code: int = 200, json_data: dict | list | None = None) -> httpx.Response:
    return httpx.Response(status_code=status_code, json=json_data if json_data is not None else {})


@pytest.mark.asyncio
async def test_list_summaries(client):
    with patch("bff.routers.summaries.get_client", new_callable=AsyncMock) as mock_get:
        mock_http = AsyncMock()
        mock_http.get.return_value = _mock_response(200, [{"id": "s-1", "summary_type": "morning"}])
        mock_get.return_value = mock_http
        response = await client.get("/api/v1/summaries")
    assert response.status_code == 200
    assert len(response.json()) == 1


@pytest.mark.asyncio
async def test_list_summaries_with_params(client):
    with patch("bff.routers.summaries.get_client", new_callable=AsyncMock) as mock_get:
        mock_http = AsyncMock()
        mock_http.get.return_value = _mock_response(200, [])
        mock_get.return_value = mock_http
        response = await client.get("/api/v1/summaries?limit=5&offset=10")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_get_daily_summary(client):
    with patch("bff.routers.summaries.get_client", new_callable=AsyncMock) as mock_get:
        mock_http = AsyncMock()
        mock_http.get.return_value = _mock_response(200, {"id": "s-1", "markdown_body": "# Morning"})
        mock_get.return_value = mock_http
        response = await client.get("/api/v1/summaries/daily?summary_type=morning&date=2026-04-04")
    assert response.status_code == 200
    assert response.json()["id"] == "s-1"


@pytest.mark.asyncio
async def test_get_daily_summary_not_found(client):
    with patch("bff.routers.summaries.get_client", new_callable=AsyncMock) as mock_get:
        mock_http = AsyncMock()
        mock_http.get.return_value = _mock_response(404, {"detail": "summary not found"})
        mock_get.return_value = mock_http
        response = await client.get("/api/v1/summaries/daily?summary_type=morning&date=2026-01-01")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_generate_daily_summary(client):
    with patch("bff.routers.summaries.get_client", new_callable=AsyncMock) as mock_get:
        mock_http = AsyncMock()
        mock_http.post.return_value = _mock_response(200, {"summary_id": "s-1", "email_count": 10})
        mock_get.return_value = mock_http
        response = await client.post("/api/v1/summaries/daily?summary_type=evening&date=2026-04-04")
    assert response.status_code == 200
    assert response.json()["summary_id"] == "s-1"


@pytest.mark.asyncio
async def test_summarize_thread(client):
    with patch("bff.routers.summaries.get_client", new_callable=AsyncMock) as mock_get:
        mock_http = AsyncMock()
        mock_http.post.return_value = _mock_response(200, {"thread_id": "th-1", "markdown": "# Thread"})
        mock_get.return_value = mock_http
        response = await client.post("/api/v1/summaries/thread/th-1")
    assert response.status_code == 200
    assert response.json()["thread_id"] == "th-1"


@pytest.mark.asyncio
async def test_summarize_thread_not_found(client):
    with patch("bff.routers.summaries.get_client", new_callable=AsyncMock) as mock_get:
        mock_http = AsyncMock()
        mock_http.post.return_value = _mock_response(404, {"detail": "no emails found for thread"})
        mock_get.return_value = mock_http
        response = await client.post("/api/v1/summaries/thread/nonexistent")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_summary_by_id(client):
    with patch("bff.routers.summaries.get_client", new_callable=AsyncMock) as mock_get:
        mock_http = AsyncMock()
        mock_http.get.return_value = _mock_response(200, {"id": "s-1", "markdown_body": "content"})
        mock_get.return_value = mock_http
        response = await client.get("/api/v1/summaries/s-1")
    assert response.status_code == 200
    assert response.json()["id"] == "s-1"


@pytest.mark.asyncio
async def test_get_summary_not_found(client):
    with patch("bff.routers.summaries.get_client", new_callable=AsyncMock) as mock_get:
        mock_http = AsyncMock()
        mock_http.get.return_value = _mock_response(404, {"detail": "summary not found"})
        mock_get.return_value = mock_http
        response = await client.get("/api/v1/summaries/nonexistent")
    assert response.status_code == 404
