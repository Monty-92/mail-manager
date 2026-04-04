import re

import structlog

logger = structlog.get_logger()

# Patterns for content to strip
_SIGNATURE_PATTERNS = [
    re.compile(r"^-- ?\n.*", re.MULTILINE | re.DOTALL),  # standard "-- " delimiter
    re.compile(r"^Sent from my (?:iPhone|iPad|Android|Galaxy).*$", re.MULTILINE),
    re.compile(r"^Get Outlook for (?:iOS|Android).*$", re.MULTILINE),
]

_QUOTED_REPLY_PATTERNS = [
    re.compile(r"^On .+ wrote:\s*$", re.MULTILINE),  # "On Mon, Jan 1, ... wrote:"
    re.compile(r"^>.*$", re.MULTILINE),  # Lines starting with >
    re.compile(r"^-{3,}\s*Original Message\s*-{3,}.*", re.MULTILINE | re.DOTALL),
    re.compile(r"^_{3,}\s*$", re.MULTILINE),  # ___ separators (Outlook)
    re.compile(r"^From:.*\nSent:.*\nTo:.*\nSubject:.*$", re.MULTILINE),  # Outlook header block
]

_DISCLAIMER_PATTERNS = [
    re.compile(
        r"(?:CONFIDENTIALITY|DISCLAIMER|PRIVILEGED|This email (?:and any|is intended)).*",
        re.IGNORECASE | re.DOTALL,
    ),
]

_EXCESSIVE_WHITESPACE = re.compile(r"\n{3,}")
_TRAILING_WHITESPACE = re.compile(r"[ \t]+$", re.MULTILINE)


def clean_email_text(text: str) -> str:
    """Clean and normalize email text for embedding generation.

    Strips signatures, quoted replies, disclaimers, and excessive whitespace.
    """
    if not text or not text.strip():
        return ""

    result = text

    # Remove quoted replies first (they can be large)
    for pattern in _QUOTED_REPLY_PATTERNS:
        result = pattern.sub("", result)

    # Remove signatures
    for pattern in _SIGNATURE_PATTERNS:
        result = pattern.sub("", result)

    # Remove disclaimers
    for pattern in _DISCLAIMER_PATTERNS:
        result = pattern.sub("", result)

    # Clean whitespace
    result = _TRAILING_WHITESPACE.sub("", result)
    result = _EXCESSIVE_WHITESPACE.sub("\n\n", result)
    result = result.strip()

    return result


def prepare_embedding_text(subject: str, sender: str, body: str) -> str:
    """Combine email fields into a single text suitable for embedding.

    Format: "Subject: <subject>\nFrom: <sender>\n\n<cleaned body>"
    """
    cleaned = clean_email_text(body)
    parts = []
    if subject:
        parts.append(f"Subject: {subject}")
    if sender:
        parts.append(f"From: {sender}")
    if cleaned:
        parts.append("")  # blank line separator
        parts.append(cleaned)
    return "\n".join(parts)
