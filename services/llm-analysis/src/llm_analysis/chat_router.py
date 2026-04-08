"""FastAPI router for the RAG chat endpoint."""

import structlog
from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from llm_analysis.chat import stream_chat_response
from llm_analysis.repository import get_pool
from llm_analysis.schemas import ChatRequest

logger = structlog.get_logger()

chat_router = APIRouter(prefix="/chat", tags=["chat"])


@chat_router.post("")
async def chat(req: ChatRequest) -> StreamingResponse:
    """Stream a RAG-powered chat response as Server-Sent Events.

    Each SSE chunk is ``data: {"token": "...", "done": false}\\n\\n``.
    The final chunk is ``data: {"done": true}\\n\\n``.
    On error: ``data: {"error": "...", "done": true}\\n\\n``.
    """
    pool = await get_pool()
    return StreamingResponse(
        stream_chat_response(pool, req.query, req.scope.value, req.scope_id, req.model),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
