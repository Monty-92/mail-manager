"""Redis pub/sub events for the summary generation service."""

import json

import redis.asyncio as redis
import structlog

from summary_generation.config import settings

logger = structlog.get_logger()

PUBLISH_CHANNEL = "mailmanager.summary.generated"

_redis_client: redis.Redis | None = None


async def get_redis() -> redis.Redis:
    """Get or create the Redis client."""
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(settings.redis_url, decode_responses=True)
        logger.info("redis client created")
    return _redis_client


async def close_redis() -> None:
    """Close the Redis client."""
    global _redis_client
    if _redis_client is not None:
        await _redis_client.aclose()
        _redis_client = None
        logger.info("redis client closed")


async def publish_summary_generated(summary_id: str, summary_type: str, date: str) -> None:
    """Publish a summary.generated event to Redis."""
    client = await get_redis()
    payload = json.dumps({"summary_id": summary_id, "summary_type": summary_type, "date": date})
    await client.publish(PUBLISH_CHANNEL, payload)
    logger.debug("published summary.generated event", summary_id=summary_id, channel=PUBLISH_CHANNEL)
