"""Ollama LLM client for email analysis."""

import json

import httpx
import structlog

from llm_analysis.config import settings

logger = structlog.get_logger()

ANALYSIS_SYSTEM_PROMPT = """You are an email analysis assistant. Analyze the email and return a JSON object with these fields:
- "category": one of "personal", "work", "transactional", "newsletter", "marketing", "notification", "spam", "other"
- "urgency": one of "critical", "high", "normal", "low", "none"
- "summary": a 1-2 sentence summary of the email
- "action_items": array of objects with "description" (string), optional "assignee" (string), optional "due_hint" (string)
- "key_topics": array of short topic strings (max 5)
- "sentiment": one of "positive", "negative", "neutral", "mixed"
- "is_junk": boolean — true if spam, marketing fluff, or no actionable content
- "confidence": float 0.0-1.0 indicating confidence in the analysis

Return ONLY valid JSON, no markdown formatting, no extra text."""

ANALYSIS_USER_TEMPLATE = """Analyze this email:

From: {sender}
To: {recipients}
Subject: {subject}
Date: {received_at}

Body:
{body}"""


async def analyze_email_text(
    sender: str,
    recipients: str,
    subject: str,
    received_at: str,
    body: str,
) -> dict:
    """Send email text to Ollama for analysis and return parsed JSON response.

    Raises:
        httpx.HTTPStatusError: If Ollama returns an error status.
        json.JSONDecodeError: If the LLM response is not valid JSON.
        KeyError: If the response is missing expected fields.
    """
    user_message = ANALYSIS_USER_TEMPLATE.format(
        sender=sender,
        recipients=recipients,
        subject=subject,
        received_at=received_at,
        body=body[:4000],  # Truncate very long emails to fit context window
    )

    payload = {
        "model": settings.ollama_model,
        "messages": [
            {"role": "system", "content": ANALYSIS_SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        "stream": False,
        "format": "json",
    }

    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(f"{settings.ollama_base_url}/api/chat", json=payload)
        response.raise_for_status()

    data = response.json()
    content = data["message"]["content"]

    logger.debug("ollama response received", model=settings.ollama_model, content_length=len(content))

    result = json.loads(content)
    return result
