"""BFF router for task management endpoints."""

import structlog
from fastapi import APIRouter, HTTPException, Query

from bff.client import get_client
from bff.config import settings

logger = structlog.get_logger()

router = APIRouter(prefix="/api/v1/tasks", tags=["tasks"])

# ─── Task List Endpoints ───


@router.get("/lists")
async def list_task_lists() -> list:
    """List all task lists ordered by position."""
    client = await get_client()
    resp = await client.get(f"{settings.task_management_url}/tasks/lists")
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.json().get("detail", "upstream error"))
    return resp.json()


@router.post("/lists", status_code=201)
async def create_task_list(body: dict) -> dict:
    """Create a new task list."""
    client = await get_client()
    resp = await client.post(f"{settings.task_management_url}/tasks/lists", json=body)
    if resp.status_code not in (200, 201):
        raise HTTPException(status_code=resp.status_code, detail=resp.json().get("detail", "upstream error"))
    return resp.json()


@router.get("/lists/{list_id}")
async def get_task_list(list_id: str) -> dict:
    """Get a task list by ID."""
    client = await get_client()
    resp = await client.get(f"{settings.task_management_url}/tasks/lists/{list_id}")
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.json().get("detail", "upstream error"))
    return resp.json()


@router.patch("/lists/{list_id}")
async def update_task_list(list_id: str, body: dict) -> dict:
    """Update a task list."""
    client = await get_client()
    resp = await client.patch(f"{settings.task_management_url}/tasks/lists/{list_id}", json=body)
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.json().get("detail", "upstream error"))
    return resp.json()


@router.delete("/lists/{list_id}", status_code=204)
async def delete_task_list(list_id: str) -> None:
    """Delete a task list."""
    client = await get_client()
    resp = await client.delete(f"{settings.task_management_url}/tasks/lists/{list_id}")
    if resp.status_code not in (204, 200):
        raise HTTPException(status_code=resp.status_code, detail=resp.json().get("detail", "upstream error"))


# ─── Task Extraction / Email Endpoints ───


@router.post("/extract/{email_id}")
async def extract_tasks(email_id: str) -> dict:
    """Extract tasks from an email's LLM analysis."""
    client = await get_client()
    resp = await client.post(f"{settings.task_management_url}/tasks/extract/{email_id}")
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.json().get("detail", "upstream error"))
    return resp.json()


@router.get("/email/{email_id}")
async def get_email_tasks(email_id: str) -> list:
    """Get all tasks created from a specific email."""
    client = await get_client()
    resp = await client.get(f"{settings.task_management_url}/tasks/email/{email_id}")
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.json().get("detail", "upstream error"))
    return resp.json()


# ─── Task CRUD Endpoints ───


@router.get("")
async def list_tasks(
    list_id: str | None = Query(None),
    status: str | None = Query(None),
    priority: str | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> list:
    """List top-level tasks with optional filters."""
    client = await get_client()
    params: dict = {"limit": limit, "offset": offset}
    if list_id:
        params["list_id"] = list_id
    if status:
        params["status"] = status
    if priority:
        params["priority"] = priority
    resp = await client.get(f"{settings.task_management_url}/tasks", params=params)
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.json().get("detail", "upstream error"))
    return resp.json()


@router.post("", status_code=201)
async def create_task(body: dict) -> dict:
    """Create a new task."""
    client = await get_client()
    resp = await client.post(f"{settings.task_management_url}/tasks", json=body)
    if resp.status_code not in (200, 201):
        raise HTTPException(status_code=resp.status_code, detail=resp.json().get("detail", "upstream error"))
    return resp.json()


@router.get("/{task_id}")
async def get_task(task_id: str) -> dict:
    """Get a task by ID with subtasks."""
    client = await get_client()
    resp = await client.get(f"{settings.task_management_url}/tasks/{task_id}")
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.json().get("detail", "upstream error"))
    return resp.json()


@router.patch("/{task_id}")
async def update_task(task_id: str, body: dict) -> dict:
    """Update a task."""
    client = await get_client()
    resp = await client.patch(f"{settings.task_management_url}/tasks/{task_id}", json=body)
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.json().get("detail", "upstream error"))
    return resp.json()


@router.delete("/{task_id}", status_code=204)
async def delete_task(task_id: str) -> None:
    """Delete a task and its subtasks."""
    client = await get_client()
    resp = await client.delete(f"{settings.task_management_url}/tasks/{task_id}")
    if resp.status_code not in (204, 200):
        raise HTTPException(status_code=resp.status_code, detail=resp.json().get("detail", "upstream error"))


@router.post("/sync/push")
async def sync_push_tasks() -> dict:
    """Push local tasks to Google Tasks."""
    client = await get_client()
    resp = await client.post(f"{settings.task_management_url}/tasks/sync/push")
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.json().get("detail", "upstream error"))
    return resp.json()


@router.post("/sync/pull")
async def sync_pull_tasks() -> dict:
    """Pull tasks from Google Tasks into local DB."""
    client = await get_client()
    resp = await client.post(f"{settings.task_management_url}/tasks/sync/pull")
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.json().get("detail", "upstream error"))
    return resp.json()


@router.post("/sync/full")
async def sync_full_tasks() -> dict:
    """Bidirectional Google Tasks sync (push then pull)."""
    client = await get_client()
    resp = await client.post(f"{settings.task_management_url}/tasks/sync/full")
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.json().get("detail", "upstream error"))
    return resp.json()
