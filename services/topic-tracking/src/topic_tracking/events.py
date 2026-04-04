"""Redis pub/sub events for the topic tracking service."""

import asyncio
import json

import redis.asyncio as redis
import structlog

from topic_tracking.config import settings
from topic_tracking.schemas import AnalyzedEvent

logger = structlog.get_logger()

SUBSCRIBE_CHANNEL = "mailmanager.email.analyzed"
PUBLISH_CHANNEL = "mailmanager.email.topics_assigned"

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


async def publish_topics_assigned(email_id: str, topic_count: int) -> None:
    """Publish a topics_assigned event to Redis."""
    client = await get_redis()
    payload = json.dumps({"email_id": email_id, "topic_count": topic_count})
    await client.publish(PUBLISH_CHANNEL, payload)
    logger.debug("published topics_assigned event", email_id=email_id, channel=PUBLISH_CHANNEL)


async def subscribe_analyzed_emails(callback) -> None:
    """Subscribe to analyzed email events and call the callback for each.

    This is a blocking loop that should run in a background task.
    The callback receives an AnalyzedEvent and should be an async function.
    """
    client = await get_redis()
    pubsub = client.pubsub()
    await pubsub.subscribe(SUBSCRIBE_CHANNEL)
    logger.info("subscribed to channel", channel=SUBSCRIBE_CHANNEL)

    try:
        async for message in pubsub.listen():
            if message["type"] != "message":
                continue
            try:
                data = json.loads(message["data"])
                event = AnalyzedEvent(**data)
                await callback(event)
            except Exception:
                logger.exception("failed to process analyzed event", raw=message.get("data"))
    except asyncio.CancelledError:
        logger.info("subscription cancelled")
    finally:
        await pubsub.unsubscribe(SUBSCRIBE_CHANNEL)
        await pubsub.aclose()
