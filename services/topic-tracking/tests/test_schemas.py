"""Tests for topic_tracking.schemas."""

from datetime import datetime, timezone

import pytest

from topic_tracking.schemas import (
    AnalyzedEvent,
    EmailForTopics,
    EmailTopicLink,
    Topic,
    TopicMatch,
    TopicSnapshot,
    TopicSummary,
)


class TestAnalyzedEvent:
    def test_create(self):
        event = AnalyzedEvent(email_id="e-1", category="work", urgency="high")
        assert event.email_id == "e-1"
        assert event.category == "work"


class TestTopicSnapshot:
    def test_create(self):
        snap = TopicSnapshot(date="2026-04-04", email_count=3, sample_subjects=["Hello", "Meeting"])
        assert snap.date == "2026-04-04"
        assert snap.email_count == 3
        assert len(snap.sample_subjects) == 2

    def test_defaults(self):
        snap = TopicSnapshot(date="2026-04-04", email_count=1)
        assert snap.sample_subjects == []


class TestTopic:
    def test_create_full(self):
        topic = Topic(
            id="t-1",
            name="Q2 Planning",
            embedding=[0.1] * 768,
            snapshots=[TopicSnapshot(date="2026-04-04", email_count=1)],
            email_count=5,
            created_at=datetime.now(tz=timezone.utc),
            updated_at=datetime.now(tz=timezone.utc),
        )
        assert topic.name == "Q2 Planning"
        assert topic.email_count == 5
        assert len(topic.embedding) == 768

    def test_defaults(self):
        topic = Topic(id="t-2", name="test")
        assert topic.embedding is None
        assert topic.snapshots == []
        assert topic.email_count == 0


class TestTopicSummary:
    def test_create(self):
        summary = TopicSummary(id="t-1", name="Meetings", email_count=10)
        assert summary.name == "Meetings"
        assert summary.email_count == 10


class TestTopicMatch:
    def test_create(self):
        match = TopicMatch(topic_id="t-1", topic_name="Budget", similarity=0.85, is_new=False)
        assert match.similarity == 0.85
        assert match.is_new is False

    def test_defaults(self):
        match = TopicMatch(topic_id="t-1", topic_name="New", similarity=1.0)
        assert match.is_new is False


class TestEmailTopicLink:
    def test_create(self):
        link = EmailTopicLink(email_id="e-1", topic_id="t-1")
        assert link.email_id == "e-1"


class TestEmailForTopics:
    def test_create(self):
        email = EmailForTopics(
            id="e-1",
            subject="Q2 Review",
            embedding=[0.5] * 768,
            key_topics=["Q2", "review"],
        )
        assert len(email.key_topics) == 2

    def test_defaults(self):
        email = EmailForTopics(id="e-2", subject="Hello")
        assert email.embedding is None
        assert email.key_topics == []
