"""Tests for ingestion repository: labels, label filtering, html_body handling."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest

from ingestion.repository import (
    _EMAIL_DETAIL_COLS,
    _EMAIL_LIST_COLS,
    _row_to_stored_email,
    get_distinct_labels,
    get_email_by_id,
    list_emails,
)


class FakeRecord(dict):
    """Dict subclass that supports attribute-style .get() and key access like asyncpg.Record."""

    def __getitem__(self, key):
        return super().__getitem__(key)


def _make_row(**overrides) -> FakeRecord:
    defaults = {
        "id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
        "provider": "gmail",
        "external_id": "ext-1",
        "thread_id": "thread-1",
        "sender": "alice@example.com",
        "recipients": ["bob@example.com"],
        "subject": "Test",
        "received_at": datetime(2024, 6, 1, tzinfo=timezone.utc),
        "labels": ["INBOX", "IMPORTANT"],
        "markdown_body": "# Hello",
        "html_body": "<h1>Hello</h1>",
        "created_at": datetime(2024, 6, 1, 0, 1, tzinfo=timezone.utc),
    }
    defaults.update(overrides)
    return FakeRecord(defaults)


class TestRowToStoredEmail:
    def test_basic_conversion(self) -> None:
        row = _make_row()
        email = _row_to_stored_email(row)
        assert email.id == "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
        assert email.provider.value == "gmail"
        assert email.sender == "alice@example.com"
        assert email.html_body == "<h1>Hello</h1>"
        assert email.labels == ["INBOX", "IMPORTANT"]

    def test_missing_html_body_defaults_empty(self) -> None:
        """When html_body is absent from the row (e.g. list query), default to empty string."""
        row = _make_row()
        del row["html_body"]
        email = _row_to_stored_email(row)
        assert email.html_body == ""


class TestColumnConstants:
    def test_list_cols_excludes_html_body(self) -> None:
        assert "html_body" not in _EMAIL_LIST_COLS

    def test_detail_cols_includes_html_body(self) -> None:
        assert "html_body" in _EMAIL_DETAIL_COLS


class TestGetDistinctLabels:
    @pytest.mark.asyncio
    async def test_returns_labels(self) -> None:
        mock_pool = AsyncMock()
        mock_pool.fetch.return_value = [
            {"label": "IMPORTANT"},
            {"label": "INBOX"},
            {"label": "Work"},
        ]
        with patch("ingestion.repository.get_pool", return_value=mock_pool):
            labels = await get_distinct_labels()
        assert labels == ["IMPORTANT", "INBOX", "Work"]
        mock_pool.fetch.assert_called_once()

    @pytest.mark.asyncio
    async def test_returns_empty_list(self) -> None:
        mock_pool = AsyncMock()
        mock_pool.fetch.return_value = []
        with patch("ingestion.repository.get_pool", return_value=mock_pool):
            labels = await get_distinct_labels()
        assert labels == []


class TestListEmailsLabelFilter:
    @pytest.mark.asyncio
    async def test_label_filter_adds_condition(self) -> None:
        """When label is provided, the query should include an ANY(labels) condition."""
        mock_pool = AsyncMock()
        mock_pool.fetchrow.return_value = {"cnt": 1}
        mock_pool.fetch.return_value = [_make_row()]

        with patch("ingestion.repository.get_pool", return_value=mock_pool):
            emails, total = await list_emails(label="INBOX")

        assert total == 1
        assert len(emails) == 1
        # Verify the label was passed as a parameter
        count_call = mock_pool.fetchrow.call_args
        assert "INBOX" in count_call.args

    @pytest.mark.asyncio
    async def test_no_label_filter(self) -> None:
        """Without label, the query should not include label conditions."""
        mock_pool = AsyncMock()
        mock_pool.fetchrow.return_value = {"cnt": 0}
        mock_pool.fetch.return_value = []

        with patch("ingestion.repository.get_pool", return_value=mock_pool):
            emails, total = await list_emails()

        assert total == 0
        assert emails == []

    @pytest.mark.asyncio
    async def test_combined_filters(self) -> None:
        """Provider + label + search should all be applied together."""
        mock_pool = AsyncMock()
        mock_pool.fetchrow.return_value = {"cnt": 2}
        mock_pool.fetch.return_value = [_make_row(), _make_row(external_id="ext-2")]

        with patch("ingestion.repository.get_pool", return_value=mock_pool):
            emails, total = await list_emails(provider="gmail", label="Work", search="hello")

        assert total == 2
        assert len(emails) == 2
        # Verify all three filter values were passed
        count_args = mock_pool.fetchrow.call_args.args
        assert "gmail" in count_args
        assert "Work" in count_args
        assert "%hello%" in count_args


class TestGetEmailById:
    @pytest.mark.asyncio
    async def test_returns_email_with_html_body(self) -> None:
        """get_email_by_id should use detail columns (includes html_body)."""
        mock_pool = AsyncMock()
        mock_pool.fetchrow.return_value = _make_row(html_body="<p>Rich content</p>")

        with patch("ingestion.repository.get_pool", return_value=mock_pool):
            email = await get_email_by_id("some-uuid")

        assert email is not None
        assert email.html_body == "<p>Rich content</p>"
        # Verify the query uses detail columns
        query = mock_pool.fetchrow.call_args.args[0]
        assert "html_body" in query

    @pytest.mark.asyncio
    async def test_returns_none_for_missing(self) -> None:
        mock_pool = AsyncMock()
        mock_pool.fetchrow.return_value = None

        with patch("ingestion.repository.get_pool", return_value=mock_pool):
            email = await get_email_by_id("nonexistent")

        assert email is None
