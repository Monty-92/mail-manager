from datetime import datetime, timezone

import pytest

from ingestion.schemas import EmailProvider, IngestResult, OAuthTokens, RawEmail, StoredEmail, SyncState


class TestRawEmail:
    def test_create_gmail_email(self) -> None:
        email = RawEmail(
            provider=EmailProvider.GMAIL,
            external_id="msg-123",
            thread_id="thread-456",
            sender="test@example.com",
            recipients=["to@example.com"],
            subject="Test",
            received_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
            html_body="<p>Hello</p>",
        )
        assert email.provider == EmailProvider.GMAIL
        assert email.external_id == "msg-123"

    def test_create_outlook_email(self) -> None:
        email = RawEmail(
            provider=EmailProvider.OUTLOOK,
            external_id="AAMk-123",
            sender="test@outlook.com",
            received_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        )
        assert email.provider == EmailProvider.OUTLOOK
        assert email.thread_id is None

    def test_defaults(self) -> None:
        email = RawEmail(
            provider=EmailProvider.GMAIL,
            external_id="x",
            sender="x@x.com",
            received_at=datetime.now(tz=timezone.utc),
        )
        assert email.recipients == []
        assert email.labels == []
        assert email.html_body == ""
        assert email.text_body == ""
        assert email.subject == ""


class TestIngestResult:
    def test_defaults(self) -> None:
        result = IngestResult(provider=EmailProvider.GMAIL)
        assert result.total_fetched == 0
        assert result.new_stored == 0
        assert result.duplicates_skipped == 0


class TestOAuthTokens:
    def test_create(self) -> None:
        tokens = OAuthTokens(access_token="abc", refresh_token="def")
        assert tokens.access_token == "abc"
        assert tokens.refresh_token == "def"
        assert tokens.token_expiry is None


class TestSyncState:
    def test_gmail(self) -> None:
        state = SyncState(provider=EmailProvider.GMAIL, history_id="12345")
        assert state.history_id == "12345"
        assert state.delta_link is None

    def test_outlook(self) -> None:
        state = SyncState(provider=EmailProvider.OUTLOOK, delta_link="https://graph/delta?token=abc")
        assert state.delta_link == "https://graph/delta?token=abc"
        assert state.history_id is None
