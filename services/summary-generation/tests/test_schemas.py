"""Tests for summary_generation.schemas."""

from datetime import date, datetime, timezone

import pytest

from summary_generation.schemas import (
    DailySummaryRequest,
    EmailDigestEntry,
    Summary,
    SummaryListItem,
    SummaryResult,
    SummaryType,
    ThreadSummaryRequest,
    TopicsAssignedEvent,
)


class TestSummaryType:
    def test_values(self):
        assert SummaryType.MORNING == "morning"
        assert SummaryType.EVENING == "evening"


class TestEmailDigestEntry:
    def test_create(self):
        entry = EmailDigestEntry(
            email_id="e-1",
            sender="alice@example.com",
            subject="Q2 Review",
            category="work",
            urgency="high",
            summary="Quarterly review discussion",
            action_items=["Review budget", "Send report"],
            key_topics=["Q2", "budget"],
        )
        assert entry.email_id == "e-1"
        assert len(entry.action_items) == 2
        assert len(entry.key_topics) == 2

    def test_defaults(self):
        entry = EmailDigestEntry(email_id="e-2", sender="bob@test.com", subject="Hello")
        assert entry.category == "other"
        assert entry.urgency == "normal"
        assert entry.summary == ""
        assert entry.action_items == []
        assert entry.key_topics == []


class TestDailySummaryRequest:
    def test_create(self):
        req = DailySummaryRequest(date=date(2026, 4, 4), summary_type=SummaryType.MORNING)
        assert req.date == date(2026, 4, 4)
        assert req.summary_type == SummaryType.MORNING


class TestThreadSummaryRequest:
    def test_create(self):
        req = ThreadSummaryRequest(thread_id="thread-123")
        assert req.thread_id == "thread-123"


class TestSummary:
    def test_create_full(self):
        summary = Summary(
            id="s-1",
            summary_type=SummaryType.MORNING,
            date=date(2026, 4, 4),
            markdown_body="# Morning Summary\n\nContent here",
            embedding=[0.1] * 768,
            diff_hash="abc123",
            topic_ids=["t-1", "t-2"],
            created_at=datetime.now(tz=timezone.utc),
        )
        assert summary.summary_type == SummaryType.MORNING
        assert len(summary.embedding) == 768
        assert len(summary.topic_ids) == 2

    def test_defaults(self):
        summary = Summary(id="s-2", summary_type=SummaryType.EVENING, date=date(2026, 4, 4), markdown_body="")
        assert summary.embedding is None
        assert summary.diff_hash is None
        assert summary.topic_ids == []
        assert summary.created_at is None


class TestSummaryListItem:
    def test_create(self):
        item = SummaryListItem(
            id="s-1",
            summary_type=SummaryType.MORNING,
            date=date(2026, 4, 4),
            diff_hash="abc123",
        )
        assert item.id == "s-1"
        assert item.diff_hash == "abc123"


class TestSummaryResult:
    def test_success(self):
        result = SummaryResult(
            summary_id="s-1",
            summary_type=SummaryType.MORNING,
            date=date(2026, 4, 4),
            email_count=15,
            topic_count=3,
            is_regenerated=True,
        )
        assert result.summary_id == "s-1"
        assert result.email_count == 15
        assert result.is_regenerated is True
        assert result.error is None

    def test_error(self):
        result = SummaryResult(
            summary_type=SummaryType.EVENING,
            date=date(2026, 4, 4),
            error="no emails found",
        )
        assert result.summary_id is None
        assert result.error == "no emails found"


class TestTopicsAssignedEvent:
    def test_create(self):
        event = TopicsAssignedEvent(email_id="e-1", topic_count=3)
        assert event.email_id == "e-1"
        assert event.topic_count == 3
