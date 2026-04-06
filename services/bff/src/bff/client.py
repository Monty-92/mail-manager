"""Shared async HTTP client for calling internal microservices."""

import httpx
import structlog

logger = structlog.get_logger()

_client: httpx.AsyncClient | None = None


async def get_client() -> httpx.AsyncClient:
    """Get or create the shared httpx async client."""
    global _client
    if _client is None:
        _client = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0, connect=10.0),
        )
        logger.info("httpx client created")
    return _client


async def close_client() -> None:
    """Close the shared httpx client."""
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None
        logger.info("httpx client closed")
