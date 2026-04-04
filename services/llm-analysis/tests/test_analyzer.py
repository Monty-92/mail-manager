"""Tests for llm_analysis.analyzer."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest

from llm_analysis.analyzer import analyze_email, parse_llm_response, handle_preprocessed_event
from llm_analysis.schemas import (
    ActionItem,
    AnalysisResult,
    EmailCategory,
    EmailForAnalysis,
    PreprocessedEvent,
    Sentiment,
    UrgencyLevel,
)


class TestParseLlmResponse:
    def test_full_valid_response(self):
        raw = {
            "category": "work",
            "urgency": "high",
            "summary": "Meeting request",
            "action_items": [{"description": "RSVP", "assignee": "me", "due_hint": "Friday"}],
            "key_topics": ["meeting", "Q2"],
            "sentiment": "positive",
            "is_junk": False,
            "confidence": 0.95,
        }
        result = parse_llm_response("e-1", raw)
        assert result.email_id == "e-1"
        assert result.category == EmailCategory.WORK
        assert result.urgency == UrgencyLevel.HIGH
        assert result.summary == "Meeting request"
        assert len(result.action_items) == 1
        assert result.action_items[0].description == "RSVP"
        assert result.key_topics == ["meeting", "Q2"]
        assert result.sentiment == Sentiment.POSITIVE
        assert result.is_junk is False
        assert result.confidence == 0.95

    def test_missing_fields_use_defaults(self):
        result = parse_llm_response("e-2", {})
        assert result.category == EmailCategory.OTHER
        assert result.urgency == UrgencyLevel.NORMAL
        assert result.summary == ""
        assert result.action_items == []
        assert result.key_topics == []
        assert result.sentiment == Sentiment.NEUTRAL
        assert result.is_junk is False
        assert result.confidence == 0.0

    def test_invalid_enum_values_fallback(self):
        raw = {"category": "bogus", "urgency": "super_urgent", "sentiment": "angry"}
        result = parse_llm_response("e-3", raw)
        assert result.category == EmailCategory.OTHER
        assert result.urgency == UrgencyLevel.NORMAL
        assert result.sentiment == Sentiment.NEUTRAL

    def test_confidence_clamped(self):
        result = parse_llm_response("e-4", {"confidence": 5.0})
        assert result.confidence == 1.0
        result2 = parse_llm_response("e-5", {"confidence": -2.0})
        assert result2.confidence == 0.0

    def test_key_topics_truncated_to_five(self):
        raw = {"key_topics": ["a", "b", "c", "d", "e", "f", "g"]}
        result = parse_llm_response("e-6", raw)
        assert len(result.key_topics) == 5

    def test_action_items_as_strings(self):
        raw = {"action_items": ["Reply to Bob", "Schedule call"]}
        result = parse_llm_response("e-7", raw)
        assert len(result.action_items) == 2
        assert result.action_items[0].description == "Reply to Bob"

    def test_action_items_malformed_entries_skipped(self):
        raw = {"action_items": [{"description": "valid"}, 42, {"no_desc": True}]}
        result = parse_llm_response("e-8", raw)
        assert len(result.action_items) == 1


_MOCK_EMAIL = EmailForAnalysis(
    id="e-1",
    provider="gmail",
    sender="alice@example.com",
    recipients=["bob@example.com"],
    subject="Test",
    markdown_body="Hello Bob, please review the doc.",
    received_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
)


class TestAnalyzeEmail:
    @pytest.mark.asyncio
    async def test_email_not_found(self):
        with patch("llm_analysis.analyzer.get_email_by_id", new_callable=AsyncMock, return_value=None):
            result = await analyze_email("missing-id")
        assert result.error == "email not found"

    @pytest.mark.asyncio
    async def test_empty_body(self):
        empty_email = _MOCK_EMAIL.model_copy(update={"markdown_body": "   "})
        with patch("llm_analysis.analyzer.get_email_by_id", new_callable=AsyncMock, return_value=empty_email):
            result = await analyze_email("e-1")
        assert result.error == "empty email body"

    @pytest.mark.asyncio
    async def test_successful_analysis(self):
        llm_raw = {
            "category": "work",
            "urgency": "normal",
            "summary": "Review request",
            "action_items": [],
            "key_topics": ["review"],
            "sentiment": "neutral",
            "is_junk": False,
            "confidence": 0.85,
        }
        with (
            patch("llm_analysis.analyzer.get_email_by_id", new_callable=AsyncMock, return_value=_MOCK_EMAIL),
            patch("llm_analysis.analyzer.analyze_email_text", new_callable=AsyncMock, return_value=llm_raw),
            patch("llm_analysis.analyzer.store_analysis", new_callable=AsyncMock, return_value=True),
        ):
            result = await analyze_email("e-1")
        assert result.category == EmailCategory.WORK
        assert result.summary == "Review request"
        assert result.error is None

    @pytest.mark.asyncio
    async def test_llm_failure(self):
        with (
            patch("llm_analysis.analyzer.get_email_by_id", new_callable=AsyncMock, return_value=_MOCK_EMAIL),
            patch(
                "llm_analysis.analyzer.analyze_email_text",
                new_callable=AsyncMock,
                side_effect=Exception("Ollama down"),
            ),
        ):
            result = await analyze_email("e-1")
        assert result.error == "llm analysis failed"

    @pytest.mark.asyncio
    async def test_store_failure(self):
        llm_raw = {"category": "personal", "summary": "Hi"}
        with (
            patch("llm_analysis.analyzer.get_email_by_id", new_callable=AsyncMock, return_value=_MOCK_EMAIL),
            patch("llm_analysis.analyzer.analyze_email_text", new_callable=AsyncMock, return_value=llm_raw),
            patch("llm_analysis.analyzer.store_analysis", new_callable=AsyncMock, return_value=False),
        ):
            result = await analyze_email("e-1")
        assert result.error == "failed to store analysis"


class TestHandlePreprocessedEvent:
    @pytest.mark.asyncio
    async def test_skips_non_completed(self):
        event = PreprocessedEvent(email_id="e-1", status="failed")
        with patch("llm_analysis.analyzer.analyze_email", new_callable=AsyncMock) as mock_analyze:
            await handle_preprocessed_event(event)
        mock_analyze.assert_not_called()

    @pytest.mark.asyncio
    async def test_calls_analyze_on_completed(self):
        event = PreprocessedEvent(email_id="e-1", status="completed")
        with patch("llm_analysis.analyzer.analyze_email", new_callable=AsyncMock) as mock_analyze:
            await handle_preprocessed_event(event)
        mock_analyze.assert_called_once_with("e-1")
