from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

import structlog
from fastapi import FastAPI

from ingestion.publisher import close_redis
from ingestion.repository import close_pool
from ingestion.router import router

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
    logger.info("ingestion service started")
    yield
    # Shutdown: close connection pools
    await close_pool()
    await close_redis()
    logger.info("ingestion service stopped")


app = FastAPI(title="Ingestion Service", version="0.1.0", lifespan=lifespan)
app.include_router(router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
