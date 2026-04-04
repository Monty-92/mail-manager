from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from bff.auth_middleware import AuthMiddleware
from bff.auth_repository import close_pool as close_auth_pool
from bff.client import close_client
from bff.routers import analysis, ingestion, preprocessing, summaries, tasks, topics
from bff.routers import accounts as accounts_router
from bff.routers import auth as auth_router
from bff.routers import calendar as calendar_router

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
    logger.info("bff service started")
    yield
    await close_client()
    await close_auth_pool()
    logger.info("bff service stopped")


app = FastAPI(title="mail-manager BFF", version="0.1.0", lifespan=lifespan)

app.add_middleware(AuthMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router.router)
app.include_router(accounts_router.router)
app.include_router(calendar_router.router)
app.include_router(ingestion.router)
app.include_router(preprocessing.router)
app.include_router(analysis.router)
app.include_router(topics.router)
app.include_router(summaries.router)
app.include_router(tasks.router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/v1/health")
async def api_health() -> dict[str, str]:
    return {"status": "ok", "version": "v1"}
