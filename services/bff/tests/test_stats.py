"""Tests for BFF stats router."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class _Row(dict):
    """asyncpg Record substitute."""
    def __getattr__(self, item):
        return self[item]


def _make_pool_with_stats():
    pool = AsyncMock()

    email_data = {
        "total_emails": 100,
        "emails_today": 5,
        "unread_emails": 12,
        "preprocessed_emails": 90,
        "analyzed_emails": 80,
    }
    task_data = {
        "active": 10,
        "overdue": 2,
        "due_this_week": 4,
        "in_progress": 3,
    }
    # fetchrow is called twice: once for email_stats, once for tasks
    pool.fetchrow = AsyncMock(side_effect=[_Row(email_data), _Row(task_data)])
    pool.fetch = AsyncMock(return_value=[])
    return pool


@pytest.mark.asyncio
async def test_get_stats(client):
    pool = _make_pool_with_stats()
    with patch("bff.routers.stats.get_pool", return_value=pool):
        response = await client.get("/api/v1/stats")
    assert response.status_code == 200
    data = response.json()
    assert "emails" in data
    assert "tasks" in data
    assert "pipeline" in data
    assert data["emails"]["total_emails"] == 100
    assert data["emails"]["unread_emails"] == 12
    assert data["tasks"]["active"] == 10


@pytest.mark.asyncio
async def test_get_pipeline_events(client):
    pool = _make_pool_with_stats()
    with patch("bff.routers.stats.get_pool", return_value=pool):
        response = await client.get("/api/v1/stats/pipeline")
    assert response.status_code == 200
    data = response.json()
    assert "events" in data
    assert isinstance(data["events"], list)
