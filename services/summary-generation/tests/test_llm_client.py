"""Tests for summary_generation.llm_client."""

import pytest

from summary_generation.llm_client import _format_email_entry, _format_email_entries
from summary_generation.schemas import EmailDigestEntry


_ENTRY_FULL = EmailDigestEntry(
    email_id="e-1",
    sender="alice@example.com",
    subject="Q2 Budget Review",
    category="work",
    urgency="high",
    summary="Discussion about Q2 budget allocation",
    action_items=["Review budget spreadsheet", "Submit proposal"],
    key_topics=["Q2", "budget"],
)

_ENTRY_MINIMAL = EmailDigestEntry(
    email_id="e-2",
    sender="bob@test.com",
    subject="Hello",
)


class TestFormatEmailEntry:
    def test_full_entry(self):
        result = _format_email_entry(_ENTRY_FULL)
        assert "alice@example.com" in result
        assert "Q2 Budget Review" in result
        assert "work" in result
        assert "high" in result
        assert "Discussion about Q2 budget" in result
        assert "Review budget spreadsheet" in result
        assert "Q2" in result

    def test_minimal_entry(self):
        result = _format_email_entry(_ENTRY_MINIMAL)
        assert "bob@test.com" in result
        assert "Hello" in result
        assert "**Summary:**" not in result
        assert "**Action Items:**" not in result
        assert "**Topics:**" not in result


class TestFormatEmailEntries:
    def test_multiple_entries(self):
        result = _format_email_entries([_ENTRY_FULL, _ENTRY_MINIMAL])
        assert "alice@example.com" in result
        assert "bob@test.com" in result

    def test_empty_list(self):
        result = _format_email_entries([])
        assert result == ""
