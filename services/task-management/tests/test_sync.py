"""Tests for Google Tasks bidirectional sync."""

from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

import pytest

from task_management.schemas import Task, TaskStatus, TaskPriority


def _make_task(task_id: str = "t-1", google_task_id: str | None = None) -> Task:
    return Task(
        id=task_id,
        title="Test task",
        status=TaskStatus.TODO,
        priority=TaskPriority.MEDIUM,
        created_at=datetime.now(tz=timezone.utc).isoformat(),
        updated_at=datetime.now(tz=timezone.utc).isoformat(),
        google_task_id=google_task_id,
    )


@pytest.mark.asyncio
async def test_push_tasks_no_accounts():
    """push_tasks_to_google should return 0 synced if no accounts."""
    from task_management.sync import push_tasks_to_google

    mock_pool = AsyncMock()
    mock_conn = AsyncMock()
    mock_conn.fetch = AsyncMock(return_value=[])  # no accounts
    mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=False)

    with patch("task_management.sync.get_pool", return_value=mock_pool):
        result = await push_tasks_to_google()

    assert result["pushed"] == 0


@pytest.mark.asyncio
async def test_pull_tasks_no_accounts():
    """pull_tasks_from_google should return 0 pulled if no accounts."""
    from task_management.sync import pull_tasks_from_google

    mock_pool = AsyncMock()
    mock_conn = AsyncMock()
    mock_conn.fetch = AsyncMock(return_value=[])  # no accounts
    mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=False)

    with patch("task_management.sync.get_pool", return_value=mock_pool):
        result = await pull_tasks_from_google()

    assert result.get("updated", result.get("pulled", 0)) == 0


@pytest.mark.asyncio
async def test_sync_push_endpoint(client):
    """POST /tasks/sync/push returns a JSON result."""
    with patch("task_management.router.push_tasks_to_google", new_callable=AsyncMock) as mock_push:
        mock_push.return_value = {"pushed": 3}
        resp = await client.post("/tasks/sync/push")
    assert resp.status_code == 200
    assert resp.json()["pushed"] == 3


@pytest.mark.asyncio
async def test_sync_pull_endpoint(client):
    """POST /tasks/sync/pull returns a JSON result."""
    with patch("task_management.router.pull_tasks_from_google", new_callable=AsyncMock) as mock_pull:
        mock_pull.return_value = {"pulled": 2}
        resp = await client.post("/tasks/sync/pull")
    assert resp.status_code == 200
    assert resp.json()["pulled"] == 2


@pytest.mark.asyncio
async def test_sync_full_endpoint(client):
    """POST /tasks/sync/full runs both push and pull."""
    with (
        patch("task_management.router.push_tasks_to_google", new_callable=AsyncMock) as mock_push,
        patch("task_management.router.pull_tasks_from_google", new_callable=AsyncMock) as mock_pull,
    ):
        mock_push.return_value = {"pushed": 1}
        mock_pull.return_value = {"pulled": 2}
        resp = await client.post("/tasks/sync/full")
    assert resp.status_code == 200
    data = resp.json()
    assert data["push"]["pushed"] == 1
    assert data["pull"]["pulled"] == 2
