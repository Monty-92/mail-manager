import base64
from datetime import datetime, timezone

import pytest

from ingestion.providers.gmail import _extract_body_parts, _parse_gmail_timestamp, _parse_recipients
from ingestion.providers.outlook import _parse_graph_message
from ingestion.schemas import EmailProvider


class TestGmailHelpers:
    def test_parse_recipients_basic(self) -> None:
        headers = {
            "to": "alice@example.com, Bob <bob@example.com>",
            "cc": "charlie@example.com",
        }
        result = _parse_recipients(headers)
        assert "alice@example.com" in result
        assert "bob@example.com" in result
        assert "charlie@example.com" in result
        assert len(result) == 3

    def test_parse_recipients_empty(self) -> None:
        assert _parse_recipients({}) == []

    def test_parse_gmail_timestamp(self) -> None:
        # 1700000000000 ms = 2023-11-14T22:13:20Z
        dt = _parse_gmail_timestamp("1700000000000")
        assert dt.year == 2023
        assert dt.tzinfo is not None

    def test_parse_gmail_timestamp_invalid(self) -> None:
        dt = _parse_gmail_timestamp("not-a-number")
        assert isinstance(dt, datetime)

    def test_extract_body_parts_plain_text(self) -> None:
        text = "Hello, World!"
        encoded = base64.urlsafe_b64encode(text.encode()).decode()
        payload = {"mimeType": "text/plain", "body": {"data": encoded}}
        html, plain = _extract_body_parts(payload)
        assert html == ""
        assert plain == "Hello, World!"

    def test_extract_body_parts_html(self) -> None:
        html_content = "<p>Hello</p>"
        encoded = base64.urlsafe_b64encode(html_content.encode()).decode()
        payload = {"mimeType": "text/html", "body": {"data": encoded}}
        html, plain = _extract_body_parts(payload)
        assert html == "<p>Hello</p>"
        assert plain == ""

    def test_extract_body_parts_multipart(self) -> None:
        text = base64.urlsafe_b64encode(b"Plain text").decode()
        html = base64.urlsafe_b64encode(b"<p>HTML</p>").decode()
        payload = {
            "mimeType": "multipart/alternative",
            "body": {},
            "parts": [
                {"mimeType": "text/plain", "body": {"data": text}},
                {"mimeType": "text/html", "body": {"data": html}},
            ],
        }
        html_out, text_out = _extract_body_parts(payload)
        assert html_out == "<p>HTML</p>"
        assert text_out == "Plain text"


class TestOutlookParser:
    def test_parse_graph_message_html(self) -> None:
        msg = {
            "id": "msg-123",
            "conversationId": "conv-456",
            "from": {"emailAddress": {"address": "sender@example.com", "name": "Sender"}},
            "toRecipients": [{"emailAddress": {"address": "to@example.com"}}],
            "ccRecipients": [{"emailAddress": {"address": "cc@example.com"}}],
            "bccRecipients": [],
            "subject": "Test Subject",
            "receivedDateTime": "2024-01-15T10:30:00Z",
            "categories": ["Work"],
            "body": {"contentType": "html", "content": "<p>Hello</p>"},
        }
        raw = _parse_graph_message(msg)
        assert raw is not None
        assert raw.provider == EmailProvider.OUTLOOK
        assert raw.external_id == "msg-123"
        assert raw.thread_id == "conv-456"
        assert raw.sender == "sender@example.com"
        assert "to@example.com" in raw.recipients
        assert "cc@example.com" in raw.recipients
        assert raw.subject == "Test Subject"
        assert raw.html_body == "<p>Hello</p>"
        assert raw.text_body == ""
        assert raw.labels == ["Work"]

    def test_parse_graph_message_text(self) -> None:
        msg = {
            "id": "msg-789",
            "from": {"emailAddress": {"address": "sender@example.com"}},
            "toRecipients": [],
            "ccRecipients": [],
            "bccRecipients": [],
            "subject": "Plain",
            "receivedDateTime": "2024-01-15T10:30:00Z",
            "categories": [],
            "body": {"contentType": "text", "content": "Hello plain"},
        }
        raw = _parse_graph_message(msg)
        assert raw is not None
        assert raw.text_body == "Hello plain"
        assert raw.html_body == ""

    def test_parse_graph_message_missing_fields(self) -> None:
        # Missing 'id' should cause KeyError → return None
        msg = {"from": {"emailAddress": {"address": "x@x.com"}}}
        raw = _parse_graph_message(msg)
        assert raw is None
