"""Tests for BFF preprocessing router."""

from unittest.mock import AsyncMock, patch

import httpx
import pytest


def _mock_response(status_code: int = 200, json_data: dict | list | None = None) -> httpx.Response:
    return httpx.Response(status_code=status_code, json=json_data if json_data is not None else {})


@pytest.mark.asyncio
async def test_preprocess_batch(client):
    with patch("bff.routers.preprocessing.get_client", new_callable=AsyncMock) as mock_get:
        mock_http = AsyncMock()
        mock_http.post.return_value = _mock_response(200, {"processed": 10})
        mock_get.return_value = mock_http
        response = await client.post("/api/v1/preprocess/batch?limit=10")
    assert response.status_code == 200
    assert response.json()["processed"] == 10


@pytest.mark.asyncio
async def test_preprocess_batch_default_limit(client):
    with patch("bff.routers.preprocessing.get_client", new_callable=AsyncMock) as mock_get:
        mock_http = AsyncMock()
        mock_http.post.return_value = _mock_response(200, {"processed": 50})
        mock_get.return_value = mock_http
        response = await client.post("/api/v1/preprocess/batch")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_preprocess_email(client):
    with patch("bff.routers.preprocessing.get_client", new_callable=AsyncMock) as mock_get:
        mock_http = AsyncMock()
        mock_http.post.return_value = _mock_response(200, {"email_id": "e-1", "status": "processed"})
        mock_get.return_value = mock_http
        response = await client.post("/api/v1/preprocess/e-1")
    assert response.status_code == 200
    assert response.json()["email_id"] == "e-1"


@pytest.mark.asyncio
async def test_preprocess_email_upstream_error(client):
    with patch("bff.routers.preprocessing.get_client", new_callable=AsyncMock) as mock_get:
        mock_http = AsyncMock()
        mock_http.post.return_value = _mock_response(404, {"detail": "email not found"})
        mock_get.return_value = mock_http
        response = await client.post("/api/v1/preprocess/nonexistent")
    assert response.status_code == 404
