"""Database repository for the task management service."""

import json
from datetime import datetime, timezone

import asyncpg
import structlog

from task_management.config import settings
from task_management.schemas import (
    ActionItem,
    Task,
    TaskCreate,
    TaskList,
    TaskListCreate,
    TaskListUpdate,
    TaskPriority,
    TaskStatus,
    TaskSummary,
    TaskUpdate,
)

logger = structlog.get_logger()

_pool: asyncpg.Pool | None = None


async def get_pool() -> asyncpg.Pool:
    """Get or create the asyncpg connection pool."""
    global _pool
    if _pool is None:
        dsn = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
        _pool = await asyncpg.create_pool(dsn, min_size=2, max_size=10, command_timeout=60)
        logger.info("database pool created")
    return _pool


async def close_pool() -> None:
    """Close the connection pool."""
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None
        logger.info("database pool closed")


# ─── Task List Operations ───


async def create_task_list(data: TaskListCreate) -> TaskList:
    """Create a new task list."""
    pool = await get_pool()
    row = await pool.fetchrow(
        """
        INSERT INTO task_lists (name, position)
        VALUES ($1, $2)
        RETURNING id, name, google_tasklist_id, position, created_at, updated_at
        """,
        data.name,
        data.position,
    )
    return _row_to_task_list(row, task_count=0)


async def get_task_list_by_id(list_id: str) -> TaskList | None:
    """Fetch a single task list with task count."""
    pool = await get_pool()
    row = await pool.fetchrow(
        """
        SELECT tl.id, tl.name, tl.google_tasklist_id, tl.position, tl.created_at, tl.updated_at,
               COUNT(t.id) AS task_count
        FROM task_lists tl
        LEFT JOIN tasks t ON tl.id = t.list_id AND t.parent_task_id IS NULL
        WHERE tl.id = $1
        GROUP BY tl.id
        """,
        list_id,
    )
    if row is None:
        return None
    return _row_to_task_list(row, task_count=int(row["task_count"]))


async def list_task_lists() -> list[TaskList]:
    """List all task lists ordered by position."""
    pool = await get_pool()
    rows = await pool.fetch(
        """
        SELECT tl.id, tl.name, tl.google_tasklist_id, tl.position, tl.created_at, tl.updated_at,
               COUNT(t.id) AS task_count
        FROM task_lists tl
        LEFT JOIN tasks t ON tl.id = t.list_id AND t.parent_task_id IS NULL
        GROUP BY tl.id
        ORDER BY tl.position ASC, tl.created_at ASC
        """
    )
    return [_row_to_task_list(row, task_count=int(row["task_count"])) for row in rows]


async def update_task_list(list_id: str, data: TaskListUpdate) -> TaskList | None:
    """Update a task list. Returns None if not found."""
    pool = await get_pool()
    sets = []
    values: list = [list_id]
    idx = 2
    if data.name is not None:
        sets.append(f"name = ${idx}")
        values.append(data.name)
        idx += 1
    if data.position is not None:
        sets.append(f"position = ${idx}")
        values.append(data.position)
        idx += 1
    if not sets:
        return await get_task_list_by_id(list_id)
    sets.append("updated_at = now()")
    query = f"UPDATE task_lists SET {', '.join(sets)} WHERE id = $1 RETURNING id, name, google_tasklist_id, position, created_at, updated_at"
    row = await pool.fetchrow(query, *values)
    if row is None:
        return None
    task_list = await get_task_list_by_id(str(row["id"]))
    return task_list


async def delete_task_list(list_id: str) -> bool:
    """Delete a task list. Tasks in the list get list_id set to NULL."""
    pool = await get_pool()
    result = await pool.execute("DELETE FROM task_lists WHERE id = $1", list_id)
    return result == "DELETE 1"


# ─── Task Operations ───


async def create_task(data: TaskCreate) -> Task:
    """Create a new task."""
    pool = await get_pool()
    # Get next position in the list
    position = 0
    if data.list_id:
        max_pos = await pool.fetchval(
            "SELECT COALESCE(MAX(position), -1) FROM tasks WHERE list_id = $1 AND parent_task_id IS NULL",
            data.list_id,
        )
        position = max_pos + 1
    elif data.parent_task_id:
        max_pos = await pool.fetchval(
            "SELECT COALESCE(MAX(position), -1) FROM tasks WHERE parent_task_id = $1",
            data.parent_task_id,
        )
        position = max_pos + 1

    row = await pool.fetchrow(
        """
        INSERT INTO tasks (title, notes, status, priority, due_date, position, list_id, parent_task_id, source_email_id, calendar_account_id)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
        RETURNING id, title, notes, status, priority, due_date, completed_at, position,
                  list_id, parent_task_id, source_email_id, google_task_id, calendar_account_id, last_synced_at,
                  created_at, updated_at
        """,
        data.title,
        data.notes,
        data.status.value,
        data.priority.value,
        data.due_date,
        position,
        data.list_id,
        data.parent_task_id,
        data.source_email_id,
        data.calendar_account_id,
    )
    logger.info("task created", task_id=str(row["id"]), title=data.title)
    return _row_to_task(row)


async def get_task_by_id(task_id: str, include_subtasks: bool = True) -> Task | None:
    """Fetch a task by ID, optionally including subtasks."""
    pool = await get_pool()
    row = await pool.fetchrow(
        """
        SELECT id, title, notes, status, priority, due_date, completed_at, position,
               list_id, parent_task_id, source_email_id, google_task_id, calendar_account_id, last_synced_at,
               created_at, updated_at
        FROM tasks
        WHERE id = $1
        """,
        task_id,
    )
    if row is None:
        return None
    task = _row_to_task(row)
    if include_subtasks:
        task.subtasks = await _get_subtasks(task_id)
    return task


async def list_tasks(
    list_id: str | None = None,
    status: TaskStatus | None = None,
    priority: TaskPriority | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[TaskSummary]:
    """List top-level tasks (no subtasks) with optional filters."""
    pool = await get_pool()
    conditions = ["t.parent_task_id IS NULL"]
    values: list = []
    idx = 1
    if list_id is not None:
        conditions.append(f"t.list_id = ${idx}")
        values.append(list_id)
        idx += 1
    if status is not None:
        conditions.append(f"t.status = ${idx}")
        values.append(status.value)
        idx += 1
    if priority is not None:
        conditions.append(f"t.priority = ${idx}")
        values.append(priority.value)
        idx += 1
    where = " AND ".join(conditions)
    values.extend([limit, offset])
    query = f"""
        SELECT t.id, t.title, t.status, t.priority, t.due_date, t.position,
               t.list_id, t.parent_task_id,
               COUNT(sub.id) AS subtask_count
        FROM tasks t
        LEFT JOIN tasks sub ON t.id = sub.parent_task_id
        WHERE {where}
        GROUP BY t.id
        ORDER BY t.position ASC, t.created_at ASC
        LIMIT ${idx} OFFSET ${idx + 1}
    """
    rows = await pool.fetch(query, *values)
    return [
        TaskSummary(
            id=str(row["id"]),
            title=row["title"],
            status=row["status"],
            priority=row["priority"],
            due_date=row["due_date"],
            position=row["position"],
            list_id=str(row["list_id"]) if row["list_id"] else None,
            parent_task_id=str(row["parent_task_id"]) if row["parent_task_id"] else None,
            subtask_count=int(row["subtask_count"]),
        )
        for row in rows
    ]


async def update_task(task_id: str, data: TaskUpdate) -> Task | None:
    """Update a task. Returns None if not found."""
    pool = await get_pool()
    sets = []
    values: list = [task_id]
    idx = 2
    if data.title is not None:
        sets.append(f"title = ${idx}")
        values.append(data.title)
        idx += 1
    if data.notes is not None:
        sets.append(f"notes = ${idx}")
        values.append(data.notes)
        idx += 1
    if data.status is not None:
        sets.append(f"status = ${idx}")
        values.append(data.status.value)
        idx += 1
        if data.status == TaskStatus.DONE:
            sets.append(f"completed_at = ${idx}")
            values.append(datetime.now(tz=timezone.utc))
            idx += 1
        elif data.status in (TaskStatus.PENDING, TaskStatus.IN_PROGRESS):
            sets.append("completed_at = NULL")
    if data.priority is not None:
        sets.append(f"priority = ${idx}")
        values.append(data.priority.value)
        idx += 1
    if data.due_date is not None:
        sets.append(f"due_date = ${idx}")
        values.append(data.due_date)
        idx += 1
    if data.list_id is not None:
        sets.append(f"list_id = ${idx}")
        values.append(data.list_id)
        idx += 1
    if data.position is not None:
        sets.append(f"position = ${idx}")
        values.append(data.position)
        idx += 1
    if not sets:
        return await get_task_by_id(task_id)
    sets.append("updated_at = now()")
    query = f"""
        UPDATE tasks SET {', '.join(sets)} WHERE id = $1
        RETURNING id, title, notes, status, priority, due_date, completed_at, position,
                  list_id, parent_task_id, source_email_id, google_task_id, last_synced_at,
                  created_at, updated_at
    """
    row = await pool.fetchrow(query, *values)
    if row is None:
        return None
    task = _row_to_task(row)
    task.subtasks = await _get_subtasks(task_id)
    return task


async def delete_task(task_id: str) -> bool:
    """Delete a task. Subtasks cascade via FK."""
    pool = await get_pool()
    result = await pool.execute("DELETE FROM tasks WHERE id = $1", task_id)
    return result == "DELETE 1"


async def get_action_items_for_email(email_id: str) -> list[ActionItem]:
    """Fetch action items from the LLM analysis for an email."""
    pool = await get_pool()
    row = await pool.fetchrow(
        "SELECT action_items FROM email_analyses WHERE email_id = $1",
        email_id,
    )
    if row is None:
        return []
    action_items_raw = row["action_items"]
    if isinstance(action_items_raw, str):
        action_items_raw = json.loads(action_items_raw)
    return [ActionItem(**item) for item in action_items_raw if isinstance(item, dict)]


async def get_tasks_for_email(email_id: str) -> list[TaskSummary]:
    """Get tasks created from a specific email."""
    pool = await get_pool()
    rows = await pool.fetch(
        """
        SELECT t.id, t.title, t.status, t.priority, t.due_date, t.position,
               t.list_id, t.parent_task_id, 0 AS subtask_count
        FROM tasks t
        WHERE t.source_email_id = $1
        ORDER BY t.position ASC
        """,
        email_id,
    )
    return [
        TaskSummary(
            id=str(row["id"]),
            title=row["title"],
            status=row["status"],
            priority=row["priority"],
            due_date=row["due_date"],
            position=row["position"],
            list_id=str(row["list_id"]) if row["list_id"] else None,
            parent_task_id=str(row["parent_task_id"]) if row["parent_task_id"] else None,
            subtask_count=0,
        )
        for row in rows
    ]


# ─── Helpers ───


async def _get_subtasks(parent_id: str) -> list[Task]:
    """Fetch immediate subtasks for a parent task."""
    pool = await get_pool()
    rows = await pool.fetch(
        """
        SELECT id, title, notes, status, priority, due_date, completed_at, position,
               list_id, parent_task_id, source_email_id, google_task_id, last_synced_at,
               created_at, updated_at
        FROM tasks
        WHERE parent_task_id = $1
        ORDER BY position ASC, created_at ASC
        """,
        parent_id,
    )
    return [_row_to_task(row) for row in rows]


def _row_to_task(row) -> Task:
    """Convert a database row to a Task model."""
    return Task(
        id=str(row["id"]),
        title=row["title"],
        notes=row["notes"],
        status=row["status"],
        priority=row["priority"],
        due_date=row["due_date"],
        completed_at=row["completed_at"],
        position=row["position"],
        list_id=str(row["list_id"]) if row["list_id"] else None,
        parent_task_id=str(row["parent_task_id"]) if row["parent_task_id"] else None,
        source_email_id=str(row["source_email_id"]) if row["source_email_id"] else None,
        google_task_id=row.get("google_task_id"),
        calendar_account_id=str(row["calendar_account_id"]) if row.get("calendar_account_id") else None,
        last_synced_at=row.get("last_synced_at"),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _row_to_task_list(row, task_count: int = 0) -> TaskList:
    """Convert a database row to a TaskList model."""
    return TaskList(
        id=str(row["id"]),
        name=row["name"],
        google_tasklist_id=row["google_tasklist_id"],
        position=row["position"],
        task_count=task_count,
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )
