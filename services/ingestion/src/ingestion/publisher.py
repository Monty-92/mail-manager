import json

import redis.asyncio as redis
import structlog

from ingestion.config import settings
from ingestion.schemas import StoredEmail

logger = structlog.get_logger()

CHANNEL = "mailmanager.email.new"

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


async def publish_new_email(email: StoredEmail) -> None:
    """Publish a new-email event to the Redis pub/sub channel."""
    client = await get_redis()
    payload = json.dumps({
        "id": email.id,
        "provider": email.provider.value,
        "external_id": email.external_id,
        "sender": email.sender,
        "subject": email.subject,
        "received_at": email.received_at.isoformat(),
    })
    await client.publish(CHANNEL, payload)
    logger.debug("published email event", email_id=email.id, channel=CHANNEL)
