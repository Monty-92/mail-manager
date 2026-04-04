import asyncio
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

import structlog
from fastapi import FastAPI

from topic_tracking.events import close_redis, subscribe_analyzed_emails
from topic_tracking.matcher import handle_analyzed_event
from topic_tracking.repository import close_pool
from topic_tracking.router import router

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    structlog.configure(
        processors=[
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer(),
        ],
    )
    logger.info("topic-tracking service started")
    subscriber_task = asyncio.create_task(subscribe_analyzed_emails(handle_analyzed_event))
    yield
    subscriber_task.cancel()
    try:
        await subscriber_task
    except asyncio.CancelledError:
        pass
    await close_pool()
    await close_redis()
    logger.info("topic-tracking service stopped")


app = FastAPI(title="Topic Tracking Service", version="0.1.0", lifespan=lifespan)
app.include_router(router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
