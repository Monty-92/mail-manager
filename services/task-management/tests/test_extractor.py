"""Tests for task_management.extractor."""

from unittest.mock import AsyncMock, patch

import pytest

from task_management.schemas import (
    ActionItem,
    AnalyzedEvent,
    Task,
    TaskExtractionResult,
    TaskPriority,
    TaskStatus,
    TaskSummary,
)
from task_management.extractor import extract_tasks_from_email, handle_analyzed_event


_MOCK_ACTION_ITEMS = [
    ActionItem(description="Send the Q4 report to finance"),
    ActionItem(description="Schedule meeting with Bob", assignee="Bob", due_hint="next week"),
]

_MOCK_TASK = Task(id="t-1", title="Send the Q4 report to finance", status=TaskStatus.PENDING, priority=TaskPriority.HIGH)


class TestExtractTasksFromEmail:
    @pytest.mark.asyncio
    async def test_creates_tasks_from_action_items(self):
        with (
            patch("task_management.extractor.get_tasks_for_email", new_callable=AsyncMock, return_value=[]),
            patch(
                "task_management.extractor.get_action_items_for_email",
                new_callable=AsyncMock,
                return_value=_MOCK_ACTION_ITEMS,
            ),
            patch("task_management.extractor.create_task", new_callable=AsyncMock, return_value=_MOCK_TASK) as mock_create,
            patch("task_management.extractor.publish_task_created", new_callable=AsyncMock) as mock_publish,
        ):
            result = await extract_tasks_from_email("e-1", urgency="high")

        assert result.email_id == "e-1"
        assert result.tasks_created == 2
        assert mock_create.call_count == 2
        assert mock_publish.call_count == 2

    @pytest.mark.asyncio
    async def test_skips_if_tasks_already_exist(self):
        existing = [TaskSummary(id="t-1", title="Existing", status=TaskStatus.PENDING, priority=TaskPriority.NONE)]
        with (
            patch("task_management.extractor.get_tasks_for_email", new_callable=AsyncMock, return_value=existing),
            patch("task_management.extractor.get_action_items_for_email", new_callable=AsyncMock) as mock_items,
        ):
            result = await extract_tasks_from_email("e-1")

        assert result.tasks_created == 0
        mock_items.assert_not_called()

    @pytest.mark.asyncio
    async def test_returns_zero_with_no_action_items(self):
        with (
            patch("task_management.extractor.get_tasks_for_email", new_callable=AsyncMock, return_value=[]),
            patch("task_management.extractor.get_action_items_for_email", new_callable=AsyncMock, return_value=[]),
        ):
            result = await extract_tasks_from_email("e-1")

        assert result.tasks_created == 0

    @pytest.mark.asyncio
    async def test_skips_empty_descriptions(self):
        items = [ActionItem(description="   "), ActionItem(description="Valid task")]
        with (
            patch("task_management.extractor.get_tasks_for_email", new_callable=AsyncMock, return_value=[]),
            patch("task_management.extractor.get_action_items_for_email", new_callable=AsyncMock, return_value=items),
            patch("task_management.extractor.create_task", new_callable=AsyncMock, return_value=_MOCK_TASK) as mock_create,
            patch("task_management.extractor.publish_task_created", new_callable=AsyncMock),
        ):
            result = await extract_tasks_from_email("e-1")

        assert result.tasks_created == 1
        mock_create.assert_called_once()

    @pytest.mark.asyncio
    async def test_urgency_mapping_critical(self):
        items = [ActionItem(description="Urgent task")]
        with (
            patch("task_management.extractor.get_tasks_for_email", new_callable=AsyncMock, return_value=[]),
            patch("task_management.extractor.get_action_items_for_email", new_callable=AsyncMock, return_value=items),
            patch("task_management.extractor.create_task", new_callable=AsyncMock, return_value=_MOCK_TASK) as mock_create,
            patch("task_management.extractor.publish_task_created", new_callable=AsyncMock),
        ):
            await extract_tasks_from_email("e-1", urgency="critical")

        call_args = mock_create.call_args[0][0]
        assert call_args.priority == TaskPriority.HIGH

    @pytest.mark.asyncio
    async def test_urgency_mapping_low(self):
        items = [ActionItem(description="Low priority task")]
        with (
            patch("task_management.extractor.get_tasks_for_email", new_callable=AsyncMock, return_value=[]),
            patch("task_management.extractor.get_action_items_for_email", new_callable=AsyncMock, return_value=items),
            patch("task_management.extractor.create_task", new_callable=AsyncMock, return_value=_MOCK_TASK) as mock_create,
            patch("task_management.extractor.publish_task_created", new_callable=AsyncMock),
        ):
            await extract_tasks_from_email("e-1", urgency="low")

        call_args = mock_create.call_args[0][0]
        assert call_args.priority == TaskPriority.LOW

    @pytest.mark.asyncio
    async def test_unknown_urgency_defaults_to_medium(self):
        items = [ActionItem(description="Some task")]
        with (
            patch("task_management.extractor.get_tasks_for_email", new_callable=AsyncMock, return_value=[]),
            patch("task_management.extractor.get_action_items_for_email", new_callable=AsyncMock, return_value=items),
            patch("task_management.extractor.create_task", new_callable=AsyncMock, return_value=_MOCK_TASK) as mock_create,
            patch("task_management.extractor.publish_task_created", new_callable=AsyncMock),
        ):
            await extract_tasks_from_email("e-1", urgency="unknown_value")

        call_args = mock_create.call_args[0][0]
        assert call_args.priority == TaskPriority.MEDIUM

    @pytest.mark.asyncio
    async def test_title_truncated_to_200_chars(self):
        long_desc = "A" * 300
        items = [ActionItem(description=long_desc)]
        with (
            patch("task_management.extractor.get_tasks_for_email", new_callable=AsyncMock, return_value=[]),
            patch("task_management.extractor.get_action_items_for_email", new_callable=AsyncMock, return_value=items),
            patch("task_management.extractor.create_task", new_callable=AsyncMock, return_value=_MOCK_TASK) as mock_create,
            patch("task_management.extractor.publish_task_created", new_callable=AsyncMock),
        ):
            await extract_tasks_from_email("e-1")

        call_args = mock_create.call_args[0][0]
        assert len(call_args.title) == 200


class TestHandleAnalyzedEvent:
    @pytest.mark.asyncio
    async def test_calls_extract_with_event_data(self):
        event = AnalyzedEvent(email_id="e-1", category="task", urgency="high")
        with patch("task_management.extractor.extract_tasks_from_email", new_callable=AsyncMock) as mock_extract:
            mock_extract.return_value = TaskExtractionResult(email_id="e-1", tasks_created=1)
            await handle_analyzed_event(event)

        mock_extract.assert_called_once_with("e-1", urgency="high")
