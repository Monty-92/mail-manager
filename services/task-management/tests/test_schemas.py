"""Tests for task_management.schemas."""

from datetime import datetime

from task_management.schemas import (
    ActionItem,
    AnalyzedEvent,
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


class TestTaskStatus:
    def test_values(self):
        assert TaskStatus.PENDING == "pending"
        assert TaskStatus.IN_PROGRESS == "in_progress"
        assert TaskStatus.DONE == "done"
        assert TaskStatus.CANCELLED == "cancelled"

    def test_all_values(self):
        assert len(TaskStatus) == 4


class TestTaskPriority:
    def test_values(self):
        assert TaskPriority.NONE == "none"
        assert TaskPriority.LOW == "low"
        assert TaskPriority.MEDIUM == "medium"
        assert TaskPriority.HIGH == "high"

    def test_all_values(self):
        assert len(TaskPriority) == 4


class TestTaskListCreate:
    def test_defaults(self):
        data = TaskListCreate(name="Work")
        assert data.name == "Work"
        assert data.position == 0

    def test_custom_position(self):
        data = TaskListCreate(name="Personal", position=5)
        assert data.position == 5


class TestTaskListUpdate:
    def test_all_none_by_default(self):
        data = TaskListUpdate()
        assert data.name is None
        assert data.position is None

    def test_partial_update(self):
        data = TaskListUpdate(name="Updated")
        assert data.name == "Updated"
        assert data.position is None


class TestTaskList:
    def test_minimal(self):
        tl = TaskList(id="l-1", name="Work")
        assert tl.id == "l-1"
        assert tl.task_count == 0
        assert tl.google_tasklist_id is None

    def test_full(self):
        now = datetime(2026, 1, 1)
        tl = TaskList(
            id="l-1", name="Work", google_tasklist_id="g-1",
            position=2, task_count=5, created_at=now, updated_at=now,
        )
        assert tl.google_tasklist_id == "g-1"
        assert tl.task_count == 5


class TestTaskCreate:
    def test_defaults(self):
        data = TaskCreate(title="Do thing")
        assert data.status == TaskStatus.PENDING
        assert data.priority == TaskPriority.NONE
        assert data.notes == ""
        assert data.due_date is None
        assert data.list_id is None
        assert data.parent_task_id is None
        assert data.source_email_id is None

    def test_full(self):
        now = datetime(2026, 6, 1)
        data = TaskCreate(
            title="Reply to Bob",
            notes="Important",
            status=TaskStatus.IN_PROGRESS,
            priority=TaskPriority.HIGH,
            due_date=now,
            list_id="l-1",
            parent_task_id="t-parent",
            source_email_id="e-1",
        )
        assert data.title == "Reply to Bob"
        assert data.priority == TaskPriority.HIGH


class TestTaskUpdate:
    def test_all_none(self):
        data = TaskUpdate()
        assert data.title is None
        assert data.status is None

    def test_partial(self):
        data = TaskUpdate(status=TaskStatus.DONE, priority=TaskPriority.LOW)
        assert data.status == TaskStatus.DONE
        assert data.title is None


class TestTask:
    def test_defaults(self):
        t = Task(id="t-1", title="Test task")
        assert t.status == TaskStatus.PENDING
        assert t.priority == TaskPriority.NONE
        assert t.subtasks == []
        assert t.completed_at is None

    def test_with_subtasks(self):
        sub = Task(id="t-2", title="Subtask")
        parent = Task(id="t-1", title="Parent", subtasks=[sub])
        assert len(parent.subtasks) == 1
        assert parent.subtasks[0].id == "t-2"


class TestTaskSummary:
    def test_basic(self):
        ts = TaskSummary(id="t-1", title="Test", status=TaskStatus.PENDING, priority=TaskPriority.NONE)
        assert ts.subtask_count == 0
        assert ts.list_id is None


class TestAnalyzedEvent:
    def test_parsing(self):
        event = AnalyzedEvent(email_id="e-1", category="task", urgency="high")
        assert event.email_id == "e-1"
        assert event.urgency == "high"


class TestActionItem:
    def test_minimal(self):
        item = ActionItem(description="Send report")
        assert item.assignee is None
        assert item.due_hint is None

    def test_full(self):
        item = ActionItem(description="Review PR", assignee="Alice", due_hint="tomorrow")
        assert item.assignee == "Alice"


class TestTaskExtractionResult:
    def test_defaults(self):
        result = TaskExtractionResult(email_id="e-1")
        assert result.tasks_created == 0
        assert result.error is None

    def test_with_count(self):
        result = TaskExtractionResult(email_id="e-1", tasks_created=3)
        assert result.tasks_created == 3
