from preprocessing.schemas import EmailEvent, EmailRecord, EmbeddingResult, PreprocessResult, PreprocessingStatus
from datetime import datetime, timezone


class TestEmailEvent:
    def test_create(self):
        event = EmailEvent(
            id="abc-123",
            provider="gmail",
            external_id="msg_001",
            sender="alice@example.com",
            subject="Hello",
            received_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        assert event.id == "abc-123"
        assert event.provider == "gmail"

    def test_from_dict(self):
        data = {
            "id": "abc-123",
            "provider": "outlook",
            "external_id": "AAM_001",
            "sender": "bob@example.com",
            "subject": "Meeting",
            "received_at": "2026-01-01T00:00:00Z",
        }
        event = EmailEvent(**data)
        assert event.provider == "outlook"
        assert event.sender == "bob@example.com"


class TestEmailRecord:
    def test_create(self):
        record = EmailRecord(
            id="uuid-1",
            provider="gmail",
            external_id="msg_001",
            sender="alice@example.com",
            subject="Test",
            markdown_body="Hello world",
            received_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        assert record.markdown_body == "Hello world"


class TestEmbeddingResult:
    def test_create(self):
        result = EmbeddingResult(
            embedding=[0.1] * 768,
            model="nomic-embed-text",
            token_count=42,
        )
        assert len(result.embedding) == 768
        assert result.model == "nomic-embed-text"

    def test_defaults(self):
        result = EmbeddingResult(embedding=[0.0], model="test")
        assert result.token_count == 0


class TestPreprocessResult:
    def test_success(self):
        result = PreprocessResult(
            email_id="uuid-1",
            cleaned_text="clean text",
            embedding_dim=768,
            status=PreprocessingStatus.COMPLETED,
        )
        assert result.status == "completed"
        assert result.error is None

    def test_failure(self):
        result = PreprocessResult(
            email_id="uuid-1",
            cleaned_text="",
            embedding_dim=0,
            status=PreprocessingStatus.FAILED,
            error="email not found",
        )
        assert result.status == "failed"
        assert result.error == "email not found"
