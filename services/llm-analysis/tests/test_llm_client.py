"""Tests for llm_analysis.llm_client."""

import json
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from llm_analysis.llm_client import analyze_email_text


class TestAnalyzeEmailText:
    @pytest.mark.asyncio
    async def test_calls_ollama_and_returns_parsed_json(self):
        """Successful Ollama call returns parsed JSON."""
        llm_response = {
            "category": "work",
            "urgency": "high",
            "summary": "Meeting request from Alice",
            "action_items": [{"description": "RSVP by Friday"}],
            "key_topics": ["meeting", "Q2 review"],
            "sentiment": "neutral",
            "is_junk": False,
            "confidence": 0.92,
        }
        mock_response = httpx.Response(
            status_code=200,
            json={"message": {"content": json.dumps(llm_response)}},
            request=httpx.Request("POST", "http://test/api/chat"),
        )

        with patch("llm_analysis.llm_client.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await analyze_email_text(
                sender="alice@example.com",
                recipients="bob@example.com",
                subject="Q2 Review Meeting",
                received_at="2026-01-15T10:00:00Z",
                body="Hi Bob, can we meet to discuss Q2?",
            )

        assert result["category"] == "work"
        assert result["urgency"] == "high"
        assert result["confidence"] == 0.92
        mock_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_raises_on_http_error(self):
        """HTTP errors from Ollama are propagated."""
        mock_response = httpx.Response(
            status_code=500,
            text="Internal Server Error",
            request=httpx.Request("POST", "http://test/api/chat"),
        )

        with patch("llm_analysis.llm_client.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            with pytest.raises(httpx.HTTPStatusError):
                await analyze_email_text(
                    sender="a@b.com",
                    recipients="c@d.com",
                    subject="Test",
                    received_at="2026-01-01T00:00:00Z",
                    body="Test body",
                )

    @pytest.mark.asyncio
    async def test_truncates_long_body(self):
        """Very long email bodies are truncated to 4000 chars."""
        llm_response = {"category": "other", "summary": "long email"}
        mock_response = httpx.Response(
            status_code=200,
            json={"message": {"content": json.dumps(llm_response)}},
            request=httpx.Request("POST", "http://test/api/chat"),
        )

        with patch("llm_analysis.llm_client.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await analyze_email_text(
                sender="a@b.com",
                recipients="c@d.com",
                subject="Test",
                received_at="2026-01-01T00:00:00Z",
                body="x" * 10000,
            )

        # Verify the post was called — body is truncated inside the function
        call_args = mock_client.post.call_args
        payload = call_args[1]["json"]
        user_msg = payload["messages"][1]["content"]
        # Body in user message should be truncated
        assert len(user_msg) < 10000
