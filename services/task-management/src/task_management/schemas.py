"""Pydantic models for the task management service."""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class TaskStatus(StrEnum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    CANCELLED = "cancelled"


class TaskPriority(StrEnum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


# ─── Task List Models ───


class TaskListCreate(BaseModel):
    """Request to create a task list."""

    name: str
    position: int = 0


class TaskListUpdate(BaseModel):
    """Request to update a task list."""

    name: str | None = None
    position: int | None = None


class TaskList(BaseModel):
    """A task list entity as stored in the database."""

    id: str
    name: str
    google_tasklist_id: str | None = None
    position: int = 0
    task_count: int = 0
    created_at: datetime | None = None
    updated_at: datetime | None = None


# ─── Task Models ───


class TaskCreate(BaseModel):
    """Request to create a task."""

    title: str
    notes: str = ""
    status: TaskStatus = TaskStatus.PENDING
    priority: TaskPriority = TaskPriority.NONE
    due_date: datetime | None = None
    list_id: str | None = None
    parent_task_id: str | None = None
    source_email_id: str | None = None


class TaskUpdate(BaseModel):
    """Request to update a task."""

    title: str | None = None
    notes: str | None = None
    status: TaskStatus | None = None
    priority: TaskPriority | None = None
    due_date: datetime | None = None
    list_id: str | None = None
    position: int | None = None


class Task(BaseModel):
    """A task entity as stored in the database."""

    id: str
    title: str
    notes: str = ""
    status: TaskStatus = TaskStatus.PENDING
    priority: TaskPriority = TaskPriority.NONE
    due_date: datetime | None = None
    completed_at: datetime | None = None
    position: int = 0
    list_id: str | None = None
    parent_task_id: str | None = None
    source_email_id: str | None = None
    google_task_id: str | None = None
    last_synced_at: datetime | None = None
    subtasks: list["Task"] = Field(default_factory=list)
    created_at: datetime | None = None
    updated_at: datetime | None = None


class TaskSummary(BaseModel):
    """Lightweight task info for list views."""

    id: str
    title: str
    status: TaskStatus
    priority: TaskPriority
    due_date: datetime | None = None
    position: int = 0
    list_id: str | None = None
    parent_task_id: str | None = None
    subtask_count: int = 0


# ─── Event Models ───


class AnalyzedEvent(BaseModel):
    """Inbound event from mailmanager.email.analyzed Redis channel."""

    email_id: str
    category: str
    urgency: str


class ActionItem(BaseModel):
    """An action item extracted from an LLM analysis."""

    description: str
    assignee: str | None = None
    due_hint: str | None = None


class TaskExtractionResult(BaseModel):
    """Result of extracting tasks from an email's analysis."""

    email_id: str
    tasks_created: int = 0
    error: str | None = None
