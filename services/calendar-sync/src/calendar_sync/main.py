from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

import structlog
from fastapi import FastAPI

from calendar_sync.calendar_repository import close_pool
from calendar_sync.router import router

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
    logger.info("calendar-sync service started")
    yield
    await close_pool()
    logger.info("calendar-sync service stopped")


app = FastAPI(title="Calendar Sync Service", version="0.1.0", lifespan=lifespan)

app.include_router(router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
