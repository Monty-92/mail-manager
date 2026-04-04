"""Tests for BFF topics router."""

from unittest.mock import AsyncMock, patch

import httpx
import pytest


def _mock_response(status_code: int = 200, json_data: dict | list | None = None) -> httpx.Response:
    return httpx.Response(status_code=status_code, json=json_data if json_data is not None else {})


@pytest.mark.asyncio
async def test_list_topics(client):
    with patch("bff.routers.topics.get_client", new_callable=AsyncMock) as mock_get:
        mock_http = AsyncMock()
        mock_http.get.return_value = _mock_response(200, [{"id": "t-1", "name": "Budget"}])
        mock_get.return_value = mock_http
        response = await client.get("/api/v1/topics")
    assert response.status_code == 200
    assert len(response.json()) == 1


@pytest.mark.asyncio
async def test_list_topics_with_params(client):
    with patch("bff.routers.topics.get_client", new_callable=AsyncMock) as mock_get:
        mock_http = AsyncMock()
        mock_http.get.return_value = _mock_response(200, [])
        mock_get.return_value = mock_http
        response = await client.get("/api/v1/topics?limit=10&offset=5")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_get_email_topics(client):
    with patch("bff.routers.topics.get_client", new_callable=AsyncMock) as mock_get:
        mock_http = AsyncMock()
        mock_http.get.return_value = _mock_response(200, [{"id": "t-1", "name": "Budget"}])
        mock_get.return_value = mock_http
        response = await client.get("/api/v1/topics/email/e-1")
    assert response.status_code == 200
    assert len(response.json()) == 1


@pytest.mark.asyncio
async def test_assign_topics(client):
    with patch("bff.routers.topics.get_client", new_callable=AsyncMock) as mock_get:
        mock_http = AsyncMock()
        mock_http.post.return_value = _mock_response(200, [{"topic_id": "t-1", "similarity": 0.95}])
        mock_get.return_value = mock_http
        response = await client.post("/api/v1/topics/assign/e-1")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_get_topic(client):
    with patch("bff.routers.topics.get_client", new_callable=AsyncMock) as mock_get:
        mock_http = AsyncMock()
        mock_http.get.return_value = _mock_response(200, {"id": "t-1", "name": "Budget"})
        mock_get.return_value = mock_http
        response = await client.get("/api/v1/topics/t-1")
    assert response.status_code == 200
    assert response.json()["name"] == "Budget"


@pytest.mark.asyncio
async def test_get_topic_not_found(client):
    with patch("bff.routers.topics.get_client", new_callable=AsyncMock) as mock_get:
        mock_http = AsyncMock()
        mock_http.get.return_value = _mock_response(404, {"detail": "topic not found"})
        mock_get.return_value = mock_http
        response = await client.get("/api/v1/topics/nonexistent")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_topic(client):
    with patch("bff.routers.topics.get_client", new_callable=AsyncMock) as mock_get:
        mock_http = AsyncMock()
        mock_http.delete.return_value = _mock_response(204)
        mock_get.return_value = mock_http
        response = await client.delete("/api/v1/topics/t-1")
    assert response.status_code == 204


@pytest.mark.asyncio
async def test_delete_topic_not_found(client):
    with patch("bff.routers.topics.get_client", new_callable=AsyncMock) as mock_get:
        mock_http = AsyncMock()
        mock_http.delete.return_value = _mock_response(404, {"detail": "topic not found"})
        mock_get.return_value = mock_http
        response = await client.delete("/api/v1/topics/nonexistent")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_topic_emails(client):
    with patch("bff.routers.topics.get_client", new_callable=AsyncMock) as mock_get:
        mock_http = AsyncMock()
        mock_http.get.return_value = _mock_response(200, ["e-1", "e-2"])
        mock_get.return_value = mock_http
        response = await client.get("/api/v1/topics/t-1/emails")
    assert response.status_code == 200
    assert response.json() == ["e-1", "e-2"]
