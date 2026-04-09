"""Tests for summary_generation.router."""

from datetime import date
from unittest.mock import AsyncMock, patch

import pytest

from summary_generation.schemas import Summary, SummaryListItem, SummaryResult, SummaryType


_MOCK_LIST_ITEM = SummaryListItem(
    id="s-1",
    summary_type=SummaryType.MORNING,
    date=date(2026, 4, 4),
    diff_hash="abc123",
)

_MOCK_SUMMARY = Summary(
    id="s-1",
    summary_type=SummaryType.MORNING,
    date=date(2026, 4, 4),
    markdown_body="# Morning Summary",
    diff_hash="abc123",
    topic_ids=["t-1"],
)

_MOCK_RESULT = SummaryResult(
    summary_id="s-1",
    summary_type=SummaryType.MORNING,
    date=date(2026, 4, 4),
    email_count=5,
    topic_count=2,
)


@pytest.mark.asyncio
async def test_list_summaries(client):
    with patch("summary_generation.router.list_summaries", new_callable=AsyncMock, return_value=[_MOCK_LIST_ITEM]):
        response = await client.get("/summaries")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["summary_type"] == "morning"


@pytest.mark.asyncio
async def test_list_summaries_empty(client):
    with patch("summary_generation.router.list_summaries", new_callable=AsyncMock, return_value=[]):
        response = await client.get("/summaries")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_list_summaries_with_params(client):
    with patch("summary_generation.router.list_summaries", new_callable=AsyncMock, return_value=[]) as mock:
        response = await client.get("/summaries?limit=10&offset=5")
    assert response.status_code == 200
    mock.assert_called_once_with(limit=10, offset=5)


@pytest.mark.asyncio
async def test_get_daily_summary(client):
    with patch("summary_generation.router.get_summary", new_callable=AsyncMock, return_value=_MOCK_SUMMARY):
        response = await client.get("/summaries/daily?summary_type=morning&date=2026-04-04")
    assert response.status_code == 200
    data = response.json()
    assert data["markdown_body"] == "# Morning Summary"


@pytest.mark.asyncio
async def test_get_daily_summary_not_found(client):
    with patch("summary_generation.router.get_summary", new_callable=AsyncMock, return_value=None):
        response = await client.get("/summaries/daily?summary_type=morning&date=2026-04-04")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_generate_daily_summary(client):
    with (
        patch("summary_generation.router.generate_daily", new_callable=AsyncMock, return_value=_MOCK_RESULT),
        patch("summary_generation.router.publish_summary_generated", new_callable=AsyncMock),
        patch("summary_generation.router.get_summary", new_callable=AsyncMock, return_value=_MOCK_SUMMARY),
    ):
        response = await client.post("/summaries/daily?summary_type=morning&date=2026-04-04")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "s-1"
    assert data["summary_type"] == "morning"


@pytest.mark.asyncio
async def test_generate_daily_summary_no_emails(client):
    no_email_result = SummaryResult(
        summary_type=SummaryType.MORNING,
        date=date(2026, 4, 4),
        email_count=0,
        error="no emails found for this date",
    )
    with patch("summary_generation.router.generate_daily", new_callable=AsyncMock, return_value=no_email_result):
        response = await client.post("/summaries/daily?summary_type=morning&date=2026-04-04")
    assert response.status_code == 422
    assert "no emails found" in response.json()["detail"]


@pytest.mark.asyncio
async def test_summarize_thread(client):
    with patch(
        "summary_generation.router.generate_thread",
        new_callable=AsyncMock,
        return_value="# Thread Summary\n\nContent",
    ):
        response = await client.post("/summaries/thread/thread-123")
    assert response.status_code == 200
    data = response.json()
    assert data["thread_id"] == "thread-123"
    assert "Thread Summary" in data["markdown"]


@pytest.mark.asyncio
async def test_summarize_thread_not_found(client):
    with patch("summary_generation.router.generate_thread", new_callable=AsyncMock, return_value=""):
        response = await client.post("/summaries/thread/thread-404")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_summary_by_id(client):
    with patch("summary_generation.router.get_summary_by_id", new_callable=AsyncMock, return_value=_MOCK_SUMMARY):
        response = await client.get("/summaries/s-1")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "s-1"


@pytest.mark.asyncio
async def test_get_summary_by_id_not_found(client):
    with patch("summary_generation.router.get_summary_by_id", new_callable=AsyncMock, return_value=None):
        response = await client.get("/summaries/nonexistent")
    assert response.status_code == 404
