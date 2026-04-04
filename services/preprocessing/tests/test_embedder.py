from unittest.mock import AsyncMock, patch

import pytest

from preprocessing.embedder import generate_embedding


class TestGenerateEmbedding:
    @pytest.mark.asyncio
    async def test_calls_ollama_and_returns_result(self):
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = lambda: None
        mock_response.json.return_value = {
            "embeddings": [[0.1] * 768],
            "model": "nomic-embed-text",
            "total_duration": 500,
        }
        # Make json() a regular function, not a coroutine
        mock_response.json = lambda: {
            "embeddings": [[0.1] * 768],
            "model": "nomic-embed-text",
            "total_duration": 500,
        }

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("preprocessing.embedder.httpx.AsyncClient", return_value=mock_client):
            result = await generate_embedding("test text")

        assert result.model == "nomic-embed-text"
        assert len(result.embedding) == 768
        mock_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_raises_on_http_error(self):
        def raise_error():
            raise Exception("Internal Server Error")

        mock_response = AsyncMock()
        mock_response.status_code = 500
        mock_response.raise_for_status = raise_error

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("preprocessing.embedder.httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(Exception, match="Internal Server Error"):
                await generate_embedding("test text")
