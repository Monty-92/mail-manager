"""Tests for topic_tracking.matcher."""

from unittest.mock import AsyncMock, patch

import pytest

from topic_tracking.matcher import assign_topics_for_email, handle_analyzed_event
from topic_tracking.schemas import AnalyzedEvent, EmailForTopics, Topic, TopicSnapshot


_MOCK_EMAIL = EmailForTopics(
    id="e-1",
    subject="Q2 Budget Review",
    embedding=[0.1] * 768,
    key_topics=["budget", "Q2 review"],
)

_MOCK_EMAIL_NO_TOPICS = EmailForTopics(
    id="e-2",
    subject="Hello",
    embedding=[0.2] * 768,
    key_topics=[],
)

_MOCK_EMAIL_NO_EMBEDDING = EmailForTopics(
    id="e-3",
    subject="Test",
    embedding=None,
    key_topics=["test topic"],
)

_MOCK_TOPIC = Topic(
    id="t-1",
    name="budget",
    embedding=[0.1] * 768,
    snapshots=[],
)


class TestAssignTopicsForEmail:
    @pytest.mark.asyncio
    async def test_email_not_found(self):
        with patch("topic_tracking.matcher.get_email_for_topics", new_callable=AsyncMock, return_value=None):
            result = await assign_topics_for_email("missing-id")
        assert result == []

    @pytest.mark.asyncio
    async def test_no_key_topics(self):
        with patch(
            "topic_tracking.matcher.get_email_for_topics",
            new_callable=AsyncMock,
            return_value=_MOCK_EMAIL_NO_TOPICS,
        ):
            result = await assign_topics_for_email("e-2")
        assert result == []

    @pytest.mark.asyncio
    async def test_exact_name_match(self):
        with (
            patch(
                "topic_tracking.matcher.get_email_for_topics",
                new_callable=AsyncMock,
                return_value=_MOCK_EMAIL,
            ),
            patch(
                "topic_tracking.matcher.find_topic_by_name",
                new_callable=AsyncMock,
                return_value=_MOCK_TOPIC,
            ),
            patch("topic_tracking.matcher.link_email_topic", new_callable=AsyncMock, return_value=True),
            patch("topic_tracking.matcher.update_topic_snapshot", new_callable=AsyncMock, return_value=True),
        ):
            result = await assign_topics_for_email("e-1")
        assert len(result) == 2
        assert result[0].topic_name == "budget"
        assert result[0].is_new is False
        assert result[0].similarity == 1.0

    @pytest.mark.asyncio
    async def test_embedding_similarity_match(self):
        with (
            patch(
                "topic_tracking.matcher.get_email_for_topics",
                new_callable=AsyncMock,
                return_value=_MOCK_EMAIL,
            ),
            patch("topic_tracking.matcher.find_topic_by_name", new_callable=AsyncMock, return_value=None),
            patch(
                "topic_tracking.matcher.find_similar_topics",
                new_callable=AsyncMock,
                return_value=[(_MOCK_TOPIC, 0.75)],
            ),
            patch("topic_tracking.matcher.link_email_topic", new_callable=AsyncMock, return_value=True),
            patch("topic_tracking.matcher.update_topic_snapshot", new_callable=AsyncMock, return_value=True),
        ):
            result = await assign_topics_for_email("e-1")
        assert len(result) == 2
        # Both topics match via similarity since find_topic_by_name returns None
        assert result[0].similarity == 0.75
        assert result[0].is_new is False

    @pytest.mark.asyncio
    async def test_creates_new_topic(self):
        new_topic = Topic(id="t-new", name="test topic", embedding=None, snapshots=[])
        with (
            patch(
                "topic_tracking.matcher.get_email_for_topics",
                new_callable=AsyncMock,
                return_value=_MOCK_EMAIL_NO_EMBEDDING,
            ),
            patch("topic_tracking.matcher.find_topic_by_name", new_callable=AsyncMock, return_value=None),
            patch("topic_tracking.matcher.create_topic", new_callable=AsyncMock, return_value=new_topic),
            patch("topic_tracking.matcher.link_email_topic", new_callable=AsyncMock, return_value=True),
            patch("topic_tracking.matcher.update_topic_snapshot", new_callable=AsyncMock, return_value=True),
        ):
            result = await assign_topics_for_email("e-3")
        assert len(result) == 1
        assert result[0].is_new is True
        assert result[0].topic_name == "test topic"

    @pytest.mark.asyncio
    async def test_skips_empty_topic_names(self):
        email_with_empty = EmailForTopics(
            id="e-4",
            subject="Test",
            embedding=None,
            key_topics=["", "  ", "valid"],
        )
        new_topic = Topic(id="t-new", name="valid", embedding=None, snapshots=[])
        with (
            patch(
                "topic_tracking.matcher.get_email_for_topics",
                new_callable=AsyncMock,
                return_value=email_with_empty,
            ),
            patch("topic_tracking.matcher.find_topic_by_name", new_callable=AsyncMock, return_value=None),
            patch("topic_tracking.matcher.create_topic", new_callable=AsyncMock, return_value=new_topic),
            patch("topic_tracking.matcher.link_email_topic", new_callable=AsyncMock, return_value=True),
            patch("topic_tracking.matcher.update_topic_snapshot", new_callable=AsyncMock, return_value=True),
        ):
            result = await assign_topics_for_email("e-4")
        assert len(result) == 1
        assert result[0].topic_name == "valid"


class TestHandleAnalyzedEvent:
    @pytest.mark.asyncio
    async def test_calls_assign(self):
        event = AnalyzedEvent(email_id="e-1", category="work", urgency="high")
        with patch("topic_tracking.matcher.assign_topics_for_email", new_callable=AsyncMock, return_value=[]) as mock:
            await handle_analyzed_event(event)
        mock.assert_called_once_with("e-1")
