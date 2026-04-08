"""RAG-based AI chat for mail-manager.

Retrieves semantically similar emails / summaries / topics to answer questions.
Streams the LLM response token-by-token via Server-Sent Events.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator

import asyncpg
import httpx
import structlog

from llm_analysis.config import settings

logger = structlog.get_logger()

# ─── Retrieval helpers ──────────────────────────────────────────────────────


async def _embed(text: str) -> list[float]:
    """Embed *text* with the configured Ollama embedding model."""
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            f"{settings.ollama_base_url}/api/embed",
            json={"model": settings.ollama_embed_model, "input": text},
        )
        resp.raise_for_status()
    return resp.json()["embeddings"][0]


async def _retrieve_context(
    pool: asyncpg.Pool,
    query_embedding: list[float],
    scope: str,
    scope_id: str | None,
    top_k: int = 5,
) -> str:
    """Fetch the most relevant chunks from the DB given the embedding query.

    Scope semantics:
    - ``global``  – search all emails + summaries + topics
    - ``topic``   – restrict email lookup to emails linked to scope_id topic
    - ``email``   – only use that single email as context
    - ``project`` – treat as global (no project table yet; future-proof label)
    """
    vec_str = "[" + ",".join(str(v) for v in query_embedding) + "]"
    chunks: list[str] = []

    if scope == "email" and scope_id:
        # Single-email context
        rows = await pool.fetch(
            """
            SELECT e.subject, e.sender, e.received_at::date AS date, e.markdown_body,
                   ea.summary, ea.category, ea.urgency
            FROM emails e
            LEFT JOIN email_analyses ea ON ea.email_id = e.id
            WHERE e.id = $1
            LIMIT 1
            """,
            scope_id,
        )
        for r in rows:
            chunks.append(
                f"[Email] {r['date']} | From: {r['sender']} | Subject: {r['subject']}\n"
                f"Category: {r['category'] or 'n/a'} | Urgency: {r['urgency'] or 'n/a'}\n"
                f"Summary: {r['summary'] or 'n/a'}\n\n{r['markdown_body'][:2000]}"
            )
    elif scope == "topic" and scope_id:
        # Emails in a topic, ranked by embedding similarity
        rows = await pool.fetch(
            f"""
            SELECT e.subject, e.sender, e.received_at::date AS date,
                   e.markdown_body, ea.summary
            FROM emails e
            JOIN email_topics et ON et.email_id = e.id
            LEFT JOIN email_analyses ea ON ea.email_id = e.id
            WHERE et.topic_id = $1 AND e.embedding IS NOT NULL
            ORDER BY e.embedding::vector(768) <=> $2::vector(768)
            LIMIT {top_k}
            """,
            scope_id,
            vec_str,
        )
        for r in rows:
            chunks.append(
                f"[Email] {r['date']} | From: {r['sender']} | Subject: {r['subject']}\n"
                f"Summary: {r['summary'] or 'n/a'}\n\n{r['markdown_body'][:1500]}"
            )
    else:
        # Global: top-k emails by cosine similarity
        rows = await pool.fetch(
            f"""
            SELECT e.subject, e.sender, e.received_at::date AS date,
                   e.markdown_body, ea.summary
            FROM emails e
            LEFT JOIN email_analyses ea ON ea.email_id = e.id
            WHERE e.embedding IS NOT NULL
            ORDER BY e.embedding::vector(768) <=> $1::vector(768)
            LIMIT {top_k}
            """,
            vec_str,
        )
        for r in rows:
            chunks.append(
                f"[Email] {r['date']} | From: {r['sender']} | Subject: {r['subject']}\n"
                f"Summary: {r['summary'] or 'n/a'}\n\n{r['markdown_body'][:1500]}"
            )

        # Top-2 recent daily summaries
        sum_rows = await pool.fetch(
            """
            SELECT summary_type, date, markdown_body
            FROM summaries
            ORDER BY date DESC, summary_type
            LIMIT 2
            """
        )
        for r in sum_rows:
            chunks.append(f"[Daily Summary – {r['summary_type']} {r['date']}]\n{r['markdown_body'][:1000]}")

    return "\n\n---\n\n".join(chunks) if chunks else "(No relevant context found.)"


CHAT_SYSTEM_PROMPT = """\
You are an intelligent email assistant for mail-manager. \
You have access to the user's emails, summaries, tasks and topics. \
Answer questions clearly and concisely. \
When citing information, mention the sender and approximate date. \
If you cannot find the answer in the provided context, say so honestly.\
"""


# ─── Streaming generator ────────────────────────────────────────────────────


async def stream_chat_response(
    pool: asyncpg.Pool,
    query: str,
    scope: str,
    scope_id: str | None,
    model: str | None = None,
) -> AsyncIterator[str]:
    """Yield SSE-formatted chunks for a RAG chat response.

    Yields ``data: <json>\\n\\n`` strings conforming to SSE spec.
    Final chunk carries ``{"done": true}``.
    """
    llm_model = model or settings.ollama_model

    try:
        query_embedding = await _embed(query)
        context_text = await _retrieve_context(pool, query_embedding, scope, scope_id)
    except Exception as exc:
        logger.error("rag retrieval failed", error=str(exc))
        yield f"data: {json.dumps({'error': 'Retrieval failed', 'done': True})}\n\n"
        return

    messages = [
        {"role": "system", "content": CHAT_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                f"Context from your emails:\n\n{context_text}\n\n"
                f"---\n\nUser question: {query}"
            ),
        },
    ]

    payload = {
        "model": llm_model,
        "messages": messages,
        "stream": True,
    }

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream("POST", f"{settings.ollama_base_url}/api/chat", json=payload) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    token = data.get("message", {}).get("content", "")
                    done = data.get("done", False)
                    if token:
                        yield f"data: {json.dumps({'token': token, 'done': False})}\n\n"
                    if done:
                        yield f"data: {json.dumps({'done': True})}\n\n"
                        return
    except Exception as exc:
        logger.error("ollama streaming error", error=str(exc))
        yield f"data: {json.dumps({'error': str(exc), 'done': True})}\n\n"
