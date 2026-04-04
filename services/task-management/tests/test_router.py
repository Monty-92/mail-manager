"""Tests for task_management.router."""

from unittest.mock import AsyncMock, patch

import pytest

from task_management.schemas import (
    Task,
    TaskExtractionResult,
    TaskList,
    TaskPriority,
    TaskStatus,
    TaskSummary,
)


_MOCK_TASK_LIST = TaskList(id="l-1", name="Work", position=0, task_count=2)
_MOCK_TASK = Task(id="t-1", title="Reply to Bob", status=TaskStatus.PENDING, priority=TaskPriority.MEDIUM)
_MOCK_TASK_SUMMARY = TaskSummary(
    id="t-1", title="Reply to Bob", status=TaskStatus.PENDING, priority=TaskPriority.MEDIUM, subtask_count=0,
)
_MOCK_EXTRACTION = TaskExtractionResult(email_id="e-1", tasks_created=2)


# ─── Task List Endpoints ───


@pytest.mark.asyncio
async def test_get_all_lists(client):
    with patch("task_management.router.list_task_lists", new_callable=AsyncMock, return_value=[_MOCK_TASK_LIST]):
        response = await client.get("/tasks/lists")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "Work"


@pytest.mark.asyncio
async def test_get_all_lists_empty(client):
    with patch("task_management.router.list_task_lists", new_callable=AsyncMock, return_value=[]):
        response = await client.get("/tasks/lists")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_create_list(client):
    with patch("task_management.router.create_task_list", new_callable=AsyncMock, return_value=_MOCK_TASK_LIST):
        response = await client.post("/tasks/lists", json={"name": "Work"})
    assert response.status_code == 201
    assert response.json()["name"] == "Work"


@pytest.mark.asyncio
async def test_get_list(client):
    with patch("task_management.router.get_task_list_by_id", new_callable=AsyncMock, return_value=_MOCK_TASK_LIST):
        response = await client.get("/tasks/lists/l-1")
    assert response.status_code == 200
    assert response.json()["id"] == "l-1"


@pytest.mark.asyncio
async def test_get_list_not_found(client):
    with patch("task_management.router.get_task_list_by_id", new_callable=AsyncMock, return_value=None):
        response = await client.get("/tasks/lists/nonexistent")
    assert response.status_code == 404
    assert response.json()["detail"] == "task list not found"


@pytest.mark.asyncio
async def test_patch_list(client):
    updated = TaskList(id="l-1", name="Updated", position=0, task_count=2)
    with patch("task_management.router.update_task_list", new_callable=AsyncMock, return_value=updated):
        response = await client.patch("/tasks/lists/l-1", json={"name": "Updated"})
    assert response.status_code == 200
    assert response.json()["name"] == "Updated"


@pytest.mark.asyncio
async def test_patch_list_not_found(client):
    with patch("task_management.router.update_task_list", new_callable=AsyncMock, return_value=None):
        response = await client.patch("/tasks/lists/nonexistent", json={"name": "X"})
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_list(client):
    with patch("task_management.router.delete_task_list", new_callable=AsyncMock, return_value=True):
        response = await client.delete("/tasks/lists/l-1")
    assert response.status_code == 204


@pytest.mark.asyncio
async def test_delete_list_not_found(client):
    with patch("task_management.router.delete_task_list", new_callable=AsyncMock, return_value=False):
        response = await client.delete("/tasks/lists/nonexistent")
    assert response.status_code == 404


# ─── Task Extraction Endpoints ───


@pytest.mark.asyncio
async def test_extract_from_email(client):
    with patch(
        "task_management.router.extract_tasks_from_email",
        new_callable=AsyncMock,
        return_value=_MOCK_EXTRACTION,
    ):
        response = await client.post("/tasks/extract/e-1")
    assert response.status_code == 200
    data = response.json()
    assert data["email_id"] == "e-1"
    assert data["tasks_created"] == 2


@pytest.mark.asyncio
async def test_extract_from_email_no_items(client):
    result = TaskExtractionResult(email_id="e-99", tasks_created=0)
    with patch(
        "task_management.router.extract_tasks_from_email",
        new_callable=AsyncMock,
        return_value=result,
    ):
        response = await client.post("/tasks/extract/e-99")
    assert response.status_code == 200
    assert response.json()["tasks_created"] == 0


@pytest.mark.asyncio
async def test_get_email_tasks(client):
    with patch(
        "task_management.router.get_tasks_for_email",
        new_callable=AsyncMock,
        return_value=[_MOCK_TASK_SUMMARY],
    ):
        response = await client.get("/tasks/email/e-1")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["title"] == "Reply to Bob"


@pytest.mark.asyncio
async def test_get_email_tasks_empty(client):
    with patch("task_management.router.get_tasks_for_email", new_callable=AsyncMock, return_value=[]):
        response = await client.get("/tasks/email/e-99")
    assert response.status_code == 200
    assert response.json() == []


# ─── Task CRUD Endpoints ───


@pytest.mark.asyncio
async def test_get_all_tasks(client):
    with patch("task_management.router.list_tasks", new_callable=AsyncMock, return_value=[_MOCK_TASK_SUMMARY]):
        response = await client.get("/tasks")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == "t-1"


@pytest.mark.asyncio
async def test_get_all_tasks_empty(client):
    with patch("task_management.router.list_tasks", new_callable=AsyncMock, return_value=[]):
        response = await client.get("/tasks")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_get_all_tasks_with_filters(client):
    with patch("task_management.router.list_tasks", new_callable=AsyncMock, return_value=[]) as mock:
        response = await client.get("/tasks?status=pending&priority=high&list_id=l-1&limit=10&offset=5")
    assert response.status_code == 200
    mock.assert_called_once_with(
        list_id="l-1",
        status=TaskStatus.PENDING,
        priority=TaskPriority.HIGH,
        limit=10,
        offset=5,
    )


@pytest.mark.asyncio
async def test_create_task(client):
    with patch("task_management.router.create_task", new_callable=AsyncMock, return_value=_MOCK_TASK):
        response = await client.post("/tasks", json={"title": "Reply to Bob"})
    assert response.status_code == 201
    assert response.json()["title"] == "Reply to Bob"


@pytest.mark.asyncio
async def test_get_task(client):
    with patch("task_management.router.get_task_by_id", new_callable=AsyncMock, return_value=_MOCK_TASK):
        response = await client.get("/tasks/t-1")
    assert response.status_code == 200
    assert response.json()["id"] == "t-1"


@pytest.mark.asyncio
async def test_get_task_not_found(client):
    with patch("task_management.router.get_task_by_id", new_callable=AsyncMock, return_value=None):
        response = await client.get("/tasks/nonexistent")
    assert response.status_code == 404
    assert response.json()["detail"] == "task not found"


@pytest.mark.asyncio
async def test_patch_task(client):
    updated = Task(id="t-1", title="Updated", status=TaskStatus.DONE, priority=TaskPriority.HIGH)
    with patch("task_management.router.update_task", new_callable=AsyncMock, return_value=updated):
        response = await client.patch("/tasks/t-1", json={"status": "done"})
    assert response.status_code == 200
    assert response.json()["status"] == "done"


@pytest.mark.asyncio
async def test_patch_task_not_found(client):
    with patch("task_management.router.update_task", new_callable=AsyncMock, return_value=None):
        response = await client.patch("/tasks/nonexistent", json={"title": "X"})
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_task(client):
    with patch("task_management.router.delete_task", new_callable=AsyncMock, return_value=True):
        response = await client.delete("/tasks/t-1")
    assert response.status_code == 204


@pytest.mark.asyncio
async def test_delete_task_not_found(client):
    with patch("task_management.router.delete_task", new_callable=AsyncMock, return_value=False):
        response = await client.delete("/tasks/nonexistent")
    assert response.status_code == 404
