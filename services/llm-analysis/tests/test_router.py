"""Tests for llm_analysis.router."""

from unittest.mock import AsyncMock, patch

import pytest

from llm_analysis.schemas import AnalysisResult, EmailCategory, UrgencyLevel


@pytest.fixture
async def client():
    from httpx import ASGITransport, AsyncClient
    from llm_analysis.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_health(client):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_get_analysis_not_found(client):
    with patch("llm_analysis.router.get_analysis_by_email_id", new_callable=AsyncMock, return_value=None):
        response = await client.get("/analyze/nonexistent-id")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_analyze_single_not_found(client):
    mock_result = AnalysisResult(email_id="missing", error="email not found")
    with patch("llm_analysis.router.analyze_email", new_callable=AsyncMock, return_value=mock_result):
        response = await client.post("/analyze/missing")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_analyze_single_success(client):
    mock_result = AnalysisResult(
        email_id="e-1",
        category=EmailCategory.WORK,
        urgency=UrgencyLevel.HIGH,
        summary="Important email",
        model_used="llama3.1:8b",
    )
    with patch("llm_analysis.router.analyze_email", new_callable=AsyncMock, return_value=mock_result):
        response = await client.post("/analyze/e-1")
    assert response.status_code == 200
    data = response.json()
    assert data["category"] == "work"
    assert data["summary"] == "Important email"


@pytest.mark.asyncio
async def test_analyze_batch(client):
    with patch("llm_analysis.router.get_unanalyzed_emails", new_callable=AsyncMock, return_value=[]):
        response = await client.post("/analyze/batch?limit=5")
    assert response.status_code == 200
    assert response.json() == []
