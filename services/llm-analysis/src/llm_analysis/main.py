import asyncio
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

import structlog
from fastapi import FastAPI

from llm_analysis.analyzer import handle_preprocessed_event
from llm_analysis.events import close_redis, subscribe_preprocessed_emails
from llm_analysis.repository import close_pool, get_pool
from llm_analysis.router import router

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
    logger.info("llm-analysis service started")

    # Eagerly initialize DB pool
    await get_pool()

    subscriber_task = asyncio.create_task(subscribe_preprocessed_emails(handle_preprocessed_event))
    yield
    subscriber_task.cancel()
    try:
        await subscriber_task
    except asyncio.CancelledError:
        pass
    await close_pool()
    await close_redis()
    logger.info("llm-analysis service stopped")


app = FastAPI(title="LLM Analysis Service", version="0.1.0", lifespan=lifespan)
app.include_router(router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
