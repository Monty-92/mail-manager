import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI

from task_management.events import close_redis, subscribe_analyzed_emails
from task_management.extractor import handle_analyzed_event
from task_management.repository import close_pool, get_pool
from task_management.router import router

logger = structlog.get_logger()

_subscriber_task: asyncio.Task | None = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    global _subscriber_task
    structlog.configure(
        processors=[
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer(),
        ],
    )
    _subscriber_task = asyncio.create_task(subscribe_analyzed_emails(handle_analyzed_event))
    logger.info("task-management service started")

    # Eagerly initialize DB pool
    await get_pool()

    yield
    if _subscriber_task is not None:
        _subscriber_task.cancel()
        try:
            await _subscriber_task
        except asyncio.CancelledError:
            pass
    await close_redis()
    await close_pool()
    logger.info("task-management service stopped")


app = FastAPI(title="Task Management Service", version="0.1.0", lifespan=lifespan)
app.include_router(router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
