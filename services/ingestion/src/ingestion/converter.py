import re

from bs4 import BeautifulSoup
from markdownify import markdownify


def html_to_markdown(html: str) -> str:
    """Convert HTML email body to clean Markdown."""
    if not html.strip():
        return ""

    soup = BeautifulSoup(html, "html.parser")

    # Remove script, style, and head tags
    for tag in soup.find_all(["script", "style", "head", "meta", "link"]):
        tag.decompose()

    # Convert to markdown
    md = markdownify(str(soup), heading_style="ATX", strip=["img"])

    # Clean up excessive whitespace
    md = re.sub(r"\n{3,}", "\n\n", md)
    md = re.sub(r"[ \t]+\n", "\n", md)
    return md.strip()


def email_body_to_markdown(html_body: str, text_body: str) -> str:
    """Convert an email body to Markdown, preferring HTML if available."""
    if html_body.strip():
        return html_to_markdown(html_body)
    # Fall back to plain text (already basically markdown-friendly)
    return text_body.strip()
