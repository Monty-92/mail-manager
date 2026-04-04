from asyncio import Task
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

import asyncio
import structlog
from fastapi import FastAPI

from preprocessing.events import close_redis, subscribe_new_emails
from preprocessing.pipeline import handle_new_email_event
from preprocessing.repository import close_pool
from preprocessing.router import router

logger = structlog.get_logger()

_subscriber_task: Task | None = None


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
    logger.info("preprocessing service started")

    # Start Redis subscriber in background
    _subscriber_task = asyncio.create_task(subscribe_new_emails(handle_new_email_event))

    yield

    # Shutdown
    if _subscriber_task is not None:
        _subscriber_task.cancel()
        try:
            await _subscriber_task
        except asyncio.CancelledError:
            pass
    await close_pool()
    await close_redis()


app = FastAPI(title="Preprocessing Service", version="0.1.0", lifespan=lifespan)
app.include_router(router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
