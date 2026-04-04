"""Tests for BFF tasks router."""

from unittest.mock import AsyncMock, patch

import httpx
import pytest


def _mock_response(status_code: int = 200, json_data: dict | list | None = None) -> httpx.Response:
    return httpx.Response(status_code=status_code, json=json_data if json_data is not None else {})


# ─── Task List Endpoints ───


@pytest.mark.asyncio
async def test_list_task_lists(client):
    with patch("bff.routers.tasks.get_client", new_callable=AsyncMock) as mock_get:
        mock_http = AsyncMock()
        mock_http.get.return_value = _mock_response(200, [{"id": "l-1", "name": "Work"}])
        mock_get.return_value = mock_http
        response = await client.get("/api/v1/tasks/lists")
    assert response.status_code == 200
    assert len(response.json()) == 1


@pytest.mark.asyncio
async def test_create_task_list(client):
    with patch("bff.routers.tasks.get_client", new_callable=AsyncMock) as mock_get:
        mock_http = AsyncMock()
        mock_http.post.return_value = _mock_response(201, {"id": "l-1", "name": "Work"})
        mock_get.return_value = mock_http
        response = await client.post("/api/v1/tasks/lists", json={"name": "Work"})
    assert response.status_code == 201
    assert response.json()["name"] == "Work"


@pytest.mark.asyncio
async def test_get_task_list(client):
    with patch("bff.routers.tasks.get_client", new_callable=AsyncMock) as mock_get:
        mock_http = AsyncMock()
        mock_http.get.return_value = _mock_response(200, {"id": "l-1", "name": "Work"})
        mock_get.return_value = mock_http
        response = await client.get("/api/v1/tasks/lists/l-1")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_get_task_list_not_found(client):
    with patch("bff.routers.tasks.get_client", new_callable=AsyncMock) as mock_get:
        mock_http = AsyncMock()
        mock_http.get.return_value = _mock_response(404, {"detail": "task list not found"})
        mock_get.return_value = mock_http
        response = await client.get("/api/v1/tasks/lists/nonexistent")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_task_list(client):
    with patch("bff.routers.tasks.get_client", new_callable=AsyncMock) as mock_get:
        mock_http = AsyncMock()
        mock_http.patch.return_value = _mock_response(200, {"id": "l-1", "name": "Updated"})
        mock_get.return_value = mock_http
        response = await client.patch("/api/v1/tasks/lists/l-1", json={"name": "Updated"})
    assert response.status_code == 200
    assert response.json()["name"] == "Updated"


@pytest.mark.asyncio
async def test_delete_task_list(client):
    with patch("bff.routers.tasks.get_client", new_callable=AsyncMock) as mock_get:
        mock_http = AsyncMock()
        mock_http.delete.return_value = _mock_response(204)
        mock_get.return_value = mock_http
        response = await client.delete("/api/v1/tasks/lists/l-1")
    assert response.status_code == 204


@pytest.mark.asyncio
async def test_delete_task_list_not_found(client):
    with patch("bff.routers.tasks.get_client", new_callable=AsyncMock) as mock_get:
        mock_http = AsyncMock()
        mock_http.delete.return_value = _mock_response(404, {"detail": "task list not found"})
        mock_get.return_value = mock_http
        response = await client.delete("/api/v1/tasks/lists/nonexistent")
    assert response.status_code == 404


# ─── Task Extraction / Email ───


@pytest.mark.asyncio
async def test_extract_tasks(client):
    with patch("bff.routers.tasks.get_client", new_callable=AsyncMock) as mock_get:
        mock_http = AsyncMock()
        mock_http.post.return_value = _mock_response(200, {"email_id": "e-1", "tasks_created": 3})
        mock_get.return_value = mock_http
        response = await client.post("/api/v1/tasks/extract/e-1")
    assert response.status_code == 200
    assert response.json()["tasks_created"] == 3


@pytest.mark.asyncio
async def test_get_email_tasks(client):
    with patch("bff.routers.tasks.get_client", new_callable=AsyncMock) as mock_get:
        mock_http = AsyncMock()
        mock_http.get.return_value = _mock_response(200, [{"id": "t-1", "title": "Reply"}])
        mock_get.return_value = mock_http
        response = await client.get("/api/v1/tasks/email/e-1")
    assert response.status_code == 200
    assert len(response.json()) == 1


@pytest.mark.asyncio
async def test_get_email_tasks_empty(client):
    with patch("bff.routers.tasks.get_client", new_callable=AsyncMock) as mock_get:
        mock_http = AsyncMock()
        mock_http.get.return_value = _mock_response(200, [])
        mock_get.return_value = mock_http
        response = await client.get("/api/v1/tasks/email/e-99")
    assert response.status_code == 200
    assert response.json() == []


# ─── Task CRUD ───


@pytest.mark.asyncio
async def test_list_tasks(client):
    with patch("bff.routers.tasks.get_client", new_callable=AsyncMock) as mock_get:
        mock_http = AsyncMock()
        mock_http.get.return_value = _mock_response(200, [{"id": "t-1", "title": "Test"}])
        mock_get.return_value = mock_http
        response = await client.get("/api/v1/tasks")
    assert response.status_code == 200
    assert len(response.json()) == 1


@pytest.mark.asyncio
async def test_list_tasks_with_filters(client):
    with patch("bff.routers.tasks.get_client", new_callable=AsyncMock) as mock_get:
        mock_http = AsyncMock()
        mock_http.get.return_value = _mock_response(200, [])
        mock_get.return_value = mock_http
        response = await client.get("/api/v1/tasks?status=pending&priority=high&list_id=l-1&limit=10&offset=5")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_create_task(client):
    with patch("bff.routers.tasks.get_client", new_callable=AsyncMock) as mock_get:
        mock_http = AsyncMock()
        mock_http.post.return_value = _mock_response(201, {"id": "t-1", "title": "New task"})
        mock_get.return_value = mock_http
        response = await client.post("/api/v1/tasks", json={"title": "New task"})
    assert response.status_code == 201
    assert response.json()["title"] == "New task"


@pytest.mark.asyncio
async def test_get_task(client):
    with patch("bff.routers.tasks.get_client", new_callable=AsyncMock) as mock_get:
        mock_http = AsyncMock()
        mock_http.get.return_value = _mock_response(200, {"id": "t-1", "title": "Test", "subtasks": []})
        mock_get.return_value = mock_http
        response = await client.get("/api/v1/tasks/t-1")
    assert response.status_code == 200
    assert response.json()["id"] == "t-1"


@pytest.mark.asyncio
async def test_get_task_not_found(client):
    with patch("bff.routers.tasks.get_client", new_callable=AsyncMock) as mock_get:
        mock_http = AsyncMock()
        mock_http.get.return_value = _mock_response(404, {"detail": "task not found"})
        mock_get.return_value = mock_http
        response = await client.get("/api/v1/tasks/nonexistent")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_task(client):
    with patch("bff.routers.tasks.get_client", new_callable=AsyncMock) as mock_get:
        mock_http = AsyncMock()
        mock_http.patch.return_value = _mock_response(200, {"id": "t-1", "status": "done"})
        mock_get.return_value = mock_http
        response = await client.patch("/api/v1/tasks/t-1", json={"status": "done"})
    assert response.status_code == 200
    assert response.json()["status"] == "done"


@pytest.mark.asyncio
async def test_update_task_not_found(client):
    with patch("bff.routers.tasks.get_client", new_callable=AsyncMock) as mock_get:
        mock_http = AsyncMock()
        mock_http.patch.return_value = _mock_response(404, {"detail": "task not found"})
        mock_get.return_value = mock_http
        response = await client.patch("/api/v1/tasks/nonexistent", json={"title": "X"})
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_task(client):
    with patch("bff.routers.tasks.get_client", new_callable=AsyncMock) as mock_get:
        mock_http = AsyncMock()
        mock_http.delete.return_value = _mock_response(204)
        mock_get.return_value = mock_http
        response = await client.delete("/api/v1/tasks/t-1")
    assert response.status_code == 204


@pytest.mark.asyncio
async def test_delete_task_not_found(client):
    with patch("bff.routers.tasks.get_client", new_callable=AsyncMock) as mock_get:
        mock_http = AsyncMock()
        mock_http.delete.return_value = _mock_response(404, {"detail": "task not found"})
        mock_get.return_value = mock_http
        response = await client.delete("/api/v1/tasks/nonexistent")
    assert response.status_code == 404
