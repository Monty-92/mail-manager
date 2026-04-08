"""BFF router for RAG-powered AI chat (proxy to llm-analysis /chat)."""

from __future__ import annotations

import structlog
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from bff.client import get_client
from bff.config import settings

logger = structlog.get_logger()

router = APIRouter(prefix="/api/v1/chat", tags=["chat"])


@router.post("")
async def chat(request: Request) -> StreamingResponse:
    """Forward a chat request to the llm-analysis service and stream the SSE response."""
    body = await request.json()
    client = await get_client()

    async def _generate():
        async with client.stream("POST", f"{settings.llm_analysis_url}/chat", json=body) as resp:
            if resp.status_code != 200:
                import json
                yield f"data: {json.dumps({'error': f'upstream error {resp.status_code}', 'done': True})}\n\n"
                return
            async for chunk in resp.aiter_bytes():
                yield chunk

    return StreamingResponse(
        _generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
