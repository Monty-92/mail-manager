"""Tests for BFF chat proxy router."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _make_mock_client(status_code: int, sse_body: bytes = b""):
    """Build a mock httpx AsyncClient whose .stream() context manager works."""
    async def _aiter_bytes():
        if sse_body:
            yield sse_body

    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    mock_resp.aiter_bytes = _aiter_bytes

    class _CM:
        async def __aenter__(self):
            return mock_resp
        async def __aexit__(self, *_):
            return False

    mock_client = MagicMock()
    mock_client.stream = MagicMock(return_value=_CM())
    return mock_client


@pytest.mark.asyncio
async def test_chat_streams_response(client):
    """Chat endpoint should stream SSE tokens from the upstream llm-analysis service."""
    sse_body = b'data: {"token": "Hello", "done": false}\n\ndata: {"done": true}\n\n'
    mock_client = _make_mock_client(200, sse_body)
    # get_client is awaited in the router, so return an AsyncMock that resolves to mock_client
    with patch("bff.routers.chat.get_client", new=AsyncMock(return_value=mock_client)):
        response = await client.post(
            "/api/v1/chat",
            json={"query": "Summarize my emails", "scope": "global"},
        )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_chat_upstream_error_yields_error_event(client):
    """When upstream returns non-200, chat yields an error SSE event (still HTTP 200)."""
    mock_client = _make_mock_client(503)
    with patch("bff.routers.chat.get_client", new=AsyncMock(return_value=mock_client)):
        response = await client.post(
            "/api/v1/chat",
            json={"query": "test", "scope": "global"},
        )
    # StreamingResponse is always 200; error is embedded in SSE payload
    assert response.status_code == 200
    assert b"error" in response.content
