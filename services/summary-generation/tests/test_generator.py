"""Tests for summary_generation.generator."""

from datetime import date
from unittest.mock import AsyncMock, patch

import pytest

from summary_generation.generator import _compute_diff_hash, generate_daily, generate_thread
from summary_generation.schemas import EmailDigestEntry, Summary, SummaryType


_MOCK_ENTRY = EmailDigestEntry(
    email_id="e-1",
    sender="alice@example.com",
    subject="Q2 Budget",
    category="work",
    urgency="high",
    summary="Budget discussion",
    action_items=["Review budget"],
    key_topics=["budget"],
)

_MOCK_SUMMARY = Summary(
    id="s-existing",
    summary_type=SummaryType.MORNING,
    date=date(2026, 4, 4),
    markdown_body="# Old Summary",
    diff_hash="oldhash",
    topic_ids=["t-1"],
)


class TestComputeDiffHash:
    def test_consistent(self):
        h1 = _compute_diff_hash("hello world")
        h2 = _compute_diff_hash("hello world")
        assert h1 == h2

    def test_different_content(self):
        h1 = _compute_diff_hash("hello")
        h2 = _compute_diff_hash("world")
        assert h1 != h2

    def test_returns_16_chars(self):
        h = _compute_diff_hash("test")
        assert len(h) == 16


class TestGenerateDaily:
    @pytest.mark.asyncio
    async def test_no_emails(self):
        with patch("summary_generation.generator.get_emails_for_date", new_callable=AsyncMock, return_value=[]):
            result = await generate_daily(date(2026, 4, 4), SummaryType.MORNING)
        assert result.email_count == 0
        assert result.error == "no emails found for this date"
        assert result.summary_id is None

    @pytest.mark.asyncio
    async def test_generates_new_summary(self):
        with (
            patch(
                "summary_generation.generator.get_emails_for_date",
                new_callable=AsyncMock,
                return_value=[_MOCK_ENTRY],
            ),
            patch("summary_generation.generator.get_summary", new_callable=AsyncMock, return_value=None),
            patch(
                "summary_generation.generator.generate_daily_summary",
                new_callable=AsyncMock,
                return_value="# Morning Summary\n\nContent",
            ),
            patch(
                "summary_generation.generator.generate_embedding",
                new_callable=AsyncMock,
                return_value=[0.1] * 768,
            ),
            patch(
                "summary_generation.generator.store_summary",
                new_callable=AsyncMock,
                return_value="s-new",
            ),
            patch(
                "summary_generation.generator.get_topic_ids_for_date",
                new_callable=AsyncMock,
                return_value=["t-1", "t-2"],
            ),
            patch("summary_generation.generator.link_summary_topics", new_callable=AsyncMock),
        ):
            result = await generate_daily(date(2026, 4, 4), SummaryType.MORNING)
        assert result.summary_id == "s-new"
        assert result.email_count == 1
        assert result.topic_count == 2
        assert result.is_regenerated is False

    @pytest.mark.asyncio
    async def test_regenerates_changed_summary(self):
        with (
            patch(
                "summary_generation.generator.get_emails_for_date",
                new_callable=AsyncMock,
                return_value=[_MOCK_ENTRY],
            ),
            patch(
                "summary_generation.generator.get_summary",
                new_callable=AsyncMock,
                return_value=_MOCK_SUMMARY,
            ),
            patch(
                "summary_generation.generator.generate_daily_summary",
                new_callable=AsyncMock,
                return_value="# New Content",
            ),
            patch(
                "summary_generation.generator.generate_embedding",
                new_callable=AsyncMock,
                return_value=[0.2] * 768,
            ),
            patch(
                "summary_generation.generator.store_summary",
                new_callable=AsyncMock,
                return_value="s-updated",
            ),
            patch(
                "summary_generation.generator.get_topic_ids_for_date",
                new_callable=AsyncMock,
                return_value=["t-1"],
            ),
            patch("summary_generation.generator.link_summary_topics", new_callable=AsyncMock),
        ):
            result = await generate_daily(date(2026, 4, 4), SummaryType.MORNING)
        assert result.summary_id == "s-updated"
        assert result.is_regenerated is True

    @pytest.mark.asyncio
    async def test_skips_unchanged_summary(self):
        """If diff_hash matches, don't re-store."""
        unchanged_body = "# Unchanged"
        existing = Summary(
            id="s-existing",
            summary_type=SummaryType.MORNING,
            date=date(2026, 4, 4),
            markdown_body=unchanged_body,
            diff_hash=_compute_diff_hash(unchanged_body),
            topic_ids=["t-1"],
        )
        with (
            patch(
                "summary_generation.generator.get_emails_for_date",
                new_callable=AsyncMock,
                return_value=[_MOCK_ENTRY],
            ),
            patch(
                "summary_generation.generator.get_summary",
                new_callable=AsyncMock,
                return_value=existing,
            ),
            patch(
                "summary_generation.generator.generate_daily_summary",
                new_callable=AsyncMock,
                return_value=unchanged_body,
            ),
        ):
            result = await generate_daily(date(2026, 4, 4), SummaryType.MORNING)
        assert result.summary_id == "s-existing"
        assert result.is_regenerated is False
        assert result.email_count == 1

    @pytest.mark.asyncio
    async def test_no_topics_for_date(self):
        with (
            patch(
                "summary_generation.generator.get_emails_for_date",
                new_callable=AsyncMock,
                return_value=[_MOCK_ENTRY],
            ),
            patch("summary_generation.generator.get_summary", new_callable=AsyncMock, return_value=None),
            patch(
                "summary_generation.generator.generate_daily_summary",
                new_callable=AsyncMock,
                return_value="# Summary",
            ),
            patch("summary_generation.generator.generate_embedding", new_callable=AsyncMock, return_value=None),
            patch(
                "summary_generation.generator.store_summary",
                new_callable=AsyncMock,
                return_value="s-1",
            ),
            patch(
                "summary_generation.generator.get_topic_ids_for_date",
                new_callable=AsyncMock,
                return_value=[],
            ),
        ):
            result = await generate_daily(date(2026, 4, 4), SummaryType.EVENING)
        assert result.topic_count == 0
        assert result.summary_id == "s-1"


class TestGenerateThread:
    @pytest.mark.asyncio
    async def test_no_emails(self):
        with patch("summary_generation.generator.get_emails_for_thread", new_callable=AsyncMock, return_value=[]):
            result = await generate_thread("thread-404")
        assert result == ""

    @pytest.mark.asyncio
    async def test_generates_thread_summary(self):
        with (
            patch(
                "summary_generation.generator.get_emails_for_thread",
                new_callable=AsyncMock,
                return_value=[_MOCK_ENTRY],
            ),
            patch(
                "summary_generation.generator.generate_thread_summary",
                new_callable=AsyncMock,
                return_value="# Thread Summary\n\nConversation about budget",
            ),
        ):
            result = await generate_thread("thread-123")
        assert "Thread Summary" in result
        assert "budget" in result
