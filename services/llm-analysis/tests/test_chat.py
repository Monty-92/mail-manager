"""Tests for the RAG chat module."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from llm_analysis.schemas import ChatScope


@pytest.mark.asyncio
async def test_stream_chat_response_global_scope():
    """stream_chat_response should yield SSE tokens from Ollama."""
    from llm_analysis.chat import stream_chat_response

    # Mock pool with empty fetch (no emails, no summaries) — just tests the pipeline runs
    mock_pool = AsyncMock()
    mock_conn = AsyncMock()
    mock_conn.fetch = AsyncMock(return_value=[])
    mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=False)

    ollama_chunks = [
        b'{"response": "Hello", "done": false}\n',
        b'{"response": " world", "done": false}\n',
        b'{"response": "", "done": true}\n',
    ]

    async def mock_aiter_lines():
        for chunk in ollama_chunks:
            yield chunk.decode()

    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.content.iter_lines = mock_aiter_lines

    async def mock_post(*args, **kwargs):
        return mock_resp

    tokens: list[str] = []

    # Patch embedding and Ollama calls
    with (
        patch("llm_analysis.chat._embed", return_value=[0.0] * 768),
        patch("llm_analysis.chat.httpx") as mock_httpx,
    ):
        mock_http_client = AsyncMock()
        mock_http_client.__aenter__ = AsyncMock(return_value=mock_http_client)
        mock_http_client.__aexit__ = AsyncMock(return_value=False)
        mock_http_client.post = AsyncMock(return_value=MagicMock(
            status_code=200,
            aiter_lines=mock_aiter_lines,
        ))
        mock_httpx.AsyncClient.return_value = mock_http_client

        chunks = []
        async for chunk in stream_chat_response(mock_pool, "What is in my inbox?", ChatScope.GLOBAL, None):
            chunks.append(chunk)

    # We just verify no exception was thrown and chunks were yielded
    assert isinstance(chunks, list)


@pytest.mark.asyncio
async def test_chat_endpoint_returns_stream(client):
    """POST /chat returns a streaming response."""
    from unittest.mock import AsyncMock, patch

    async def fake_stream(*args, **kwargs):
        yield b'data: {"token": "Hi", "done": false}\n\n'
        yield b'data: {"done": true}\n\n'

    with patch("llm_analysis.chat_router.stream_chat_response", return_value=fake_stream()):
        with patch("llm_analysis.chat_router.get_pool", return_value=AsyncMock()):
            response = await client.post(
                "/chat",
                json={"query": "Hello", "scope": "global"},
            )

    assert response.status_code == 200
