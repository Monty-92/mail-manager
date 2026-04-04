"""Ollama LLM client for summary generation."""

import json

import httpx
import structlog

from summary_generation.config import settings
from summary_generation.schemas import EmailDigestEntry

logger = structlog.get_logger()

DAILY_SYSTEM_PROMPT = """You are a personal email assistant generating a daily email digest summary.
Given a list of emails received on a specific date, produce a well-structured Markdown summary.

The summary MUST include:
1. A header with the date and summary type (morning/evening)
2. A quick stats line (total emails, urgent items count, action items count)
3. **Urgent & Important** section — emails with urgency "critical" or "high"
4. **Action Items** section — all action items extracted from emails
5. **By Category** section — brief overview grouped by email category
6. **Key Topics** section — the main topics that appeared across emails

Format the output as clean Markdown. Be concise but informative.
Return ONLY the Markdown content, no JSON wrapping."""

DAILY_USER_TEMPLATE = """Generate a {summary_type} summary for {date}.

Emails received ({email_count} total):

{email_entries}"""

THREAD_SYSTEM_PROMPT = """You are a personal email assistant summarizing an email thread/conversation.
Given a sequence of emails in a thread, produce a concise Markdown summary.

The summary MUST include:
1. A header with the thread subject
2. **Participants** — who is involved in the conversation
3. **Timeline** — brief chronological overview of the conversation flow
4. **Key Points** — the main decisions, requests, or information exchanged
5. **Action Items** — any outstanding tasks or next steps
6. **Current Status** — where the conversation stands

Format the output as clean Markdown. Be concise but capture the essential information.
Return ONLY the Markdown content, no JSON wrapping."""

THREAD_USER_TEMPLATE = """Summarize this email thread ({email_count} emails):

{email_entries}"""


def _format_email_entry(entry: EmailDigestEntry) -> str:
    """Format a single email digest entry for the LLM prompt."""
    parts = [
        f"- **From:** {entry.sender}",
        f"  **Subject:** {entry.subject}",
        f"  **Category:** {entry.category} | **Urgency:** {entry.urgency}",
    ]
    if entry.summary:
        parts.append(f"  **Summary:** {entry.summary}")
    if entry.action_items:
        items = "; ".join(entry.action_items[:5])
        parts.append(f"  **Action Items:** {items}")
    if entry.key_topics:
        parts.append(f"  **Topics:** {', '.join(entry.key_topics[:5])}")
    return "\n".join(parts)


def _format_email_entries(entries: list[EmailDigestEntry]) -> str:
    """Format all email entries for the LLM prompt."""
    return "\n\n".join(_format_email_entry(e) for e in entries)


async def generate_daily_summary(
    summary_type: str,
    target_date: str,
    entries: list[EmailDigestEntry],
) -> str:
    """Generate a daily digest summary via Ollama. Returns Markdown text."""
    email_entries_text = _format_email_entries(entries)
    user_message = DAILY_USER_TEMPLATE.format(
        summary_type=summary_type,
        date=target_date,
        email_count=len(entries),
        email_entries=email_entries_text,
    )

    return await _call_ollama(DAILY_SYSTEM_PROMPT, user_message)


async def generate_thread_summary(entries: list[EmailDigestEntry]) -> str:
    """Generate a thread conversation summary via Ollama. Returns Markdown text."""
    email_entries_text = _format_email_entries(entries)
    user_message = THREAD_USER_TEMPLATE.format(
        email_count=len(entries),
        email_entries=email_entries_text,
    )

    return await _call_ollama(THREAD_SYSTEM_PROMPT, user_message)


async def generate_embedding(text: str) -> list[float] | None:
    """Generate an embedding for the summary text via Ollama."""
    try:
        payload = {"model": settings.embedding_model, "input": text}
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(f"{settings.ollama_base_url}/api/embed", json=payload)
            response.raise_for_status()
        data = response.json()
        embeddings = data.get("embeddings", [])
        if embeddings:
            return embeddings[0]
        return None
    except Exception:
        logger.exception("failed to generate embedding")
        return None


async def _call_ollama(system_prompt: str, user_message: str) -> str:
    """Send a prompt to Ollama and return the text response."""
    payload = {
        "model": settings.ollama_model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        "stream": False,
    }

    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(f"{settings.ollama_base_url}/api/chat", json=payload)
        response.raise_for_status()

    data = response.json()
    content = data["message"]["content"]
    logger.debug("ollama response received", model=settings.ollama_model, content_length=len(content))
    return content
