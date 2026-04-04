"""FastAPI router for the task management service."""

import structlog
from fastapi import APIRouter, HTTPException, Query

from task_management.extractor import extract_tasks_from_email
from task_management.repository import (
    create_task,
    create_task_list,
    delete_task,
    delete_task_list,
    get_task_by_id,
    get_task_list_by_id,
    get_tasks_for_email,
    list_task_lists,
    list_tasks,
    update_task,
    update_task_list,
)
from task_management.schemas import (
    Task,
    TaskCreate,
    TaskExtractionResult,
    TaskList,
    TaskListCreate,
    TaskListUpdate,
    TaskPriority,
    TaskStatus,
    TaskSummary,
    TaskUpdate,
)

logger = structlog.get_logger()

router = APIRouter(prefix="/tasks", tags=["tasks"])

# ─── Task List Endpoints ───


@router.get("/lists", response_model=list[TaskList])
async def get_all_lists() -> list[TaskList]:
    """List all task lists ordered by position."""
    return await list_task_lists()


@router.post("/lists", response_model=TaskList, status_code=201)
async def create_list(data: TaskListCreate) -> TaskList:
    """Create a new task list."""
    return await create_task_list(data)


@router.get("/lists/{list_id}", response_model=TaskList)
async def get_list(list_id: str) -> TaskList:
    """Get a task list by ID."""
    task_list = await get_task_list_by_id(list_id)
    if task_list is None:
        raise HTTPException(status_code=404, detail="task list not found")
    return task_list


@router.patch("/lists/{list_id}", response_model=TaskList)
async def patch_list(list_id: str, data: TaskListUpdate) -> TaskList:
    """Update a task list."""
    task_list = await update_task_list(list_id, data)
    if task_list is None:
        raise HTTPException(status_code=404, detail="task list not found")
    return task_list


@router.delete("/lists/{list_id}", status_code=204)
async def remove_list(list_id: str) -> None:
    """Delete a task list."""
    deleted = await delete_task_list(list_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="task list not found")


# ─── Task Extraction Endpoints (before /{task_id}) ───


@router.post("/extract/{email_id}", response_model=TaskExtractionResult)
async def extract_from_email(email_id: str) -> TaskExtractionResult:
    """Extract tasks from an email's LLM analysis action items."""
    return await extract_tasks_from_email(email_id)


@router.get("/email/{email_id}", response_model=list[TaskSummary])
async def get_email_tasks(email_id: str) -> list[TaskSummary]:
    """Get all tasks created from a specific email."""
    return await get_tasks_for_email(email_id)


# ─── Task CRUD Endpoints ───


@router.get("", response_model=list[TaskSummary])
async def get_all_tasks(
    list_id: str | None = Query(None, description="Filter by task list"),
    status: TaskStatus | None = Query(None, description="Filter by status"),
    priority: TaskPriority | None = Query(None, description="Filter by priority"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> list[TaskSummary]:
    """List top-level tasks with optional filters."""
    return await list_tasks(list_id=list_id, status=status, priority=priority, limit=limit, offset=offset)


@router.post("", response_model=Task, status_code=201)
async def create_new_task(data: TaskCreate) -> Task:
    """Create a new task."""
    return await create_task(data)


@router.get("/{task_id}", response_model=Task)
async def get_task(task_id: str) -> Task:
    """Get a task by ID with subtasks."""
    task = await get_task_by_id(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="task not found")
    return task


@router.patch("/{task_id}", response_model=Task)
async def patch_task(task_id: str, data: TaskUpdate) -> Task:
    """Update a task."""
    task = await update_task(task_id, data)
    if task is None:
        raise HTTPException(status_code=404, detail="task not found")
    return task


@router.delete("/{task_id}", status_code=204)
async def remove_task(task_id: str) -> None:
    """Delete a task and its subtasks."""
    deleted = await delete_task(task_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="task not found")
