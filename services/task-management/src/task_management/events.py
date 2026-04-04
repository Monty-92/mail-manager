"""Redis pub/sub events for the task management service."""

import asyncio
import json

import redis.asyncio as redis
import structlog

from task_management.config import settings
from task_management.schemas import AnalyzedEvent

logger = structlog.get_logger()

SUBSCRIBE_CHANNEL = "mailmanager.email.analyzed"
PUBLISH_CHANNEL = "mailmanager.task.created"

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


async def publish_task_created(task_id: str, email_id: str) -> None:
    """Publish a task.created event to Redis."""
    client = await get_redis()
    payload = json.dumps({"task_id": task_id, "email_id": email_id})
    await client.publish(PUBLISH_CHANNEL, payload)
    logger.debug("published task.created event", task_id=task_id, channel=PUBLISH_CHANNEL)


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
