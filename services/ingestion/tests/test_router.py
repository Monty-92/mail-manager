import pytest
from httpx import ASGITransport, AsyncClient

from ingestion.main import app


@pytest.mark.asyncio
async def test_get_auth_url_gmail():
    """Test that auth URL endpoint returns a valid Google OAuth URL."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/ingest/auth/url/gmail")
        assert response.status_code == 200
        data = response.json()
        assert data["provider"] == "gmail"
        assert "accounts.google.com" in data["auth_url"]


@pytest.mark.asyncio
async def test_get_auth_url_outlook():
    """Test that auth URL endpoint returns a valid Microsoft OAuth URL."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/ingest/auth/url/outlook")
        assert response.status_code == 200
        data = response.json()
        assert data["provider"] == "outlook"
        assert "login.microsoftonline.com" in data["auth_url"]


@pytest.mark.asyncio
async def test_get_auth_url_invalid_provider():
    """Test that invalid provider returns 422."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/ingest/auth/url/invalid")
        assert response.status_code == 422


@pytest.mark.asyncio
async def test_sync_without_auth(client):
    """Test that sync endpoint returns 401 when not authenticated."""
    response = await client.post("/ingest/sync/gmail")
    assert response.status_code == 401
    assert "No accounts connected" in response.json()["detail"]


@pytest.mark.asyncio
async def test_fetch_without_auth(client):
    """Test that fetch endpoint returns 401 when not authenticated."""
    response = await client.post("/ingest/fetch/outlook")
    assert response.status_code == 401
    assert "No accounts connected" in response.json()["detail"]
