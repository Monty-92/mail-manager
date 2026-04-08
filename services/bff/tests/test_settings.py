"""Tests for BFF settings router."""

from unittest.mock import AsyncMock, patch

import pytest


class _Row(dict):
    """Minimal asyncpg Record substitute that supports dict-style and attribute access."""
    def __getattr__(self, item):
        return self[item]


@pytest.mark.asyncio
async def test_get_settings(client):
    rows = [
        _Row(key="llm_model", value="llama3.1:8b"),
        _Row(key="embed_model", value="nomic-embed-text"),
    ]
    mock_pool = AsyncMock()
    mock_pool.fetch.return_value = rows
    with patch("bff.routers.settings.get_pool", return_value=mock_pool):
        response = await client.get("/api/v1/settings")
    assert response.status_code == 200
    data = response.json()
    assert data["llm_model"] == "llama3.1:8b"
    assert data["embed_model"] == "nomic-embed-text"


@pytest.mark.asyncio
async def test_patch_setting(client):
    mock_pool = AsyncMock()
    mock_pool.execute = AsyncMock()
    with patch("bff.routers.settings.get_pool", return_value=mock_pool):
        response = await client.patch("/api/v1/settings/llm_model", json={"value": "mistral:7b"})
    assert response.status_code == 200
    assert response.json()["value"] == "mistral:7b"


@pytest.mark.asyncio
async def test_patch_unknown_key_rejected(client):
    mock_pool = AsyncMock()
    with patch("bff.routers.settings.get_pool", return_value=mock_pool):
        response = await client.patch("/api/v1/settings/unknown_key", json={"value": "x"})
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_put_settings(client):
    mock_pool = AsyncMock()
    mock_pool.execute = AsyncMock()
    mock_pool.fetch.return_value = [_Row(key="llm_model", value="mistral:7b")]
    with patch("bff.routers.settings.get_pool", return_value=mock_pool):
        response = await client.put("/api/v1/settings", json={"llm_model": "mistral:7b"})
    assert response.status_code == 200
    data = response.json()
    assert data["llm_model"] == "mistral:7b"


@pytest.mark.asyncio
async def test_put_settings_unknown_key_rejected(client):
    mock_pool = AsyncMock()
    with patch("bff.routers.settings.get_pool", return_value=mock_pool):
        response = await client.put("/api/v1/settings", json={"bad_key": "x"})
    assert response.status_code == 400

