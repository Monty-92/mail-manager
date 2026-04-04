from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest

from preprocessing.pipeline import preprocess_email
from preprocessing.schemas import EmailRecord, PreprocessingStatus


class TestPreprocessEmail:
    @pytest.mark.asyncio
    async def test_email_not_found(self):
        with patch("preprocessing.pipeline.get_email_by_id", new_callable=AsyncMock, return_value=None):
            result = await preprocess_email("nonexistent-id")
        assert result.status == PreprocessingStatus.FAILED
        assert result.error == "email not found"

    @pytest.mark.asyncio
    async def test_empty_body_after_cleaning(self):
        email = EmailRecord(
            id="uuid-1",
            provider="gmail",
            external_id="msg_001",
            sender="",
            subject="",
            markdown_body="",
            received_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        with patch("preprocessing.pipeline.get_email_by_id", new_callable=AsyncMock, return_value=email):
            result = await preprocess_email("uuid-1")
        assert result.status == PreprocessingStatus.FAILED
        assert result.error == "empty text after cleaning"

    @pytest.mark.asyncio
    async def test_successful_preprocessing(self):
        email = EmailRecord(
            id="uuid-1",
            provider="gmail",
            external_id="msg_001",
            sender="alice@test.com",
            subject="Project Update",
            markdown_body="The project is going well.",
            received_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        mock_embedding_result = AsyncMock()
        mock_embedding_result.embedding = [0.1] * 768

        with (
            patch("preprocessing.pipeline.get_email_by_id", new_callable=AsyncMock, return_value=email),
            patch("preprocessing.pipeline.generate_embedding", new_callable=AsyncMock, return_value=mock_embedding_result),
            patch("preprocessing.pipeline.store_embedding", new_callable=AsyncMock, return_value=True),
            patch("preprocessing.pipeline.publish_preprocessed", new_callable=AsyncMock),
        ):
            result = await preprocess_email("uuid-1")

        assert result.status == PreprocessingStatus.COMPLETED
        assert result.embedding_dim == 768
        assert "Project Update" in result.cleaned_text

    @pytest.mark.asyncio
    async def test_store_embedding_failure(self):
        email = EmailRecord(
            id="uuid-1",
            provider="gmail",
            external_id="msg_001",
            sender="alice@test.com",
            subject="Test",
            markdown_body="Content here",
            received_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        mock_embedding_result = AsyncMock()
        mock_embedding_result.embedding = [0.1] * 768

        with (
            patch("preprocessing.pipeline.get_email_by_id", new_callable=AsyncMock, return_value=email),
            patch("preprocessing.pipeline.generate_embedding", new_callable=AsyncMock, return_value=mock_embedding_result),
            patch("preprocessing.pipeline.store_embedding", new_callable=AsyncMock, return_value=False),
        ):
            result = await preprocess_email("uuid-1")

        assert result.status == PreprocessingStatus.FAILED
        assert result.error == "failed to store embedding"

    @pytest.mark.asyncio
    async def test_embedding_generation_exception(self):
        email = EmailRecord(
            id="uuid-1",
            provider="gmail",
            external_id="msg_001",
            sender="alice@test.com",
            subject="Test",
            markdown_body="Content",
            received_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )

        with (
            patch("preprocessing.pipeline.get_email_by_id", new_callable=AsyncMock, return_value=email),
            patch("preprocessing.pipeline.generate_embedding", new_callable=AsyncMock, side_effect=Exception("Ollama down")),
            patch("preprocessing.pipeline.publish_preprocessed", new_callable=AsyncMock),
        ):
            result = await preprocess_email("uuid-1")

        assert result.status == PreprocessingStatus.FAILED
        assert "Ollama down" in result.error
