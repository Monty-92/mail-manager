"""Tests for llm_analysis.schemas."""

from datetime import datetime, timezone

import pytest

from llm_analysis.schemas import (
    ActionItem,
    AnalysisResult,
    EmailCategory,
    EmailForAnalysis,
    PreprocessedEvent,
    Sentiment,
    StoredAnalysis,
    UrgencyLevel,
)


class TestEnums:
    def test_email_category_values(self):
        assert EmailCategory.PERSONAL == "personal"
        assert EmailCategory.SPAM == "spam"
        assert len(EmailCategory) == 8

    def test_urgency_level_values(self):
        assert UrgencyLevel.CRITICAL == "critical"
        assert UrgencyLevel.NONE == "none"
        assert len(UrgencyLevel) == 5

    def test_sentiment_values(self):
        assert Sentiment.POSITIVE == "positive"
        assert Sentiment.MIXED == "mixed"
        assert len(Sentiment) == 4


class TestActionItem:
    def test_create_full(self):
        item = ActionItem(description="Reply to Bob", assignee="me", due_hint="by Friday")
        assert item.description == "Reply to Bob"
        assert item.assignee == "me"
        assert item.due_hint == "by Friday"

    def test_create_minimal(self):
        item = ActionItem(description="Follow up")
        assert item.assignee is None
        assert item.due_hint is None


class TestPreprocessedEvent:
    def test_create(self):
        event = PreprocessedEvent(email_id="abc-123", status="completed")
        assert event.email_id == "abc-123"
        assert event.status == "completed"


class TestEmailForAnalysis:
    def test_create(self):
        email = EmailForAnalysis(
            id="e-1",
            provider="gmail",
            sender="alice@example.com",
            recipients=["bob@example.com"],
            subject="Hello",
            markdown_body="Hi Bob",
            received_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        assert email.id == "e-1"
        assert email.provider == "gmail"
        assert email.recipients == ["bob@example.com"]


class TestAnalysisResult:
    def test_defaults(self):
        result = AnalysisResult(email_id="e-1")
        assert result.category == EmailCategory.OTHER
        assert result.urgency == UrgencyLevel.NORMAL
        assert result.summary == ""
        assert result.action_items == []
        assert result.key_topics == []
        assert result.sentiment == Sentiment.NEUTRAL
        assert result.is_junk is False
        assert result.confidence == 0.0
        assert result.error is None

    def test_full(self):
        result = AnalysisResult(
            email_id="e-1",
            category=EmailCategory.WORK,
            urgency=UrgencyLevel.HIGH,
            summary="Important meeting request",
            action_items=[ActionItem(description="RSVP")],
            key_topics=["meeting", "Q2"],
            sentiment=Sentiment.POSITIVE,
            is_junk=False,
            confidence=0.95,
            model_used="llama3.1:8b",
        )
        assert result.category == EmailCategory.WORK
        assert len(result.action_items) == 1


class TestStoredAnalysis:
    def test_create(self):
        now = datetime.now(tz=timezone.utc)
        stored = StoredAnalysis(
            id="a-1",
            email_id="e-1",
            category=EmailCategory.PERSONAL,
            urgency=UrgencyLevel.LOW,
            summary="Friendly note",
            action_items=[],
            key_topics=["greetings"],
            sentiment=Sentiment.POSITIVE,
            is_junk=False,
            confidence=0.8,
            model_used="llama3.1:8b",
            created_at=now,
            updated_at=now,
        )
        assert stored.id == "a-1"
        assert stored.email_id == "e-1"
