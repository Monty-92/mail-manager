from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
import asyncio

import structlog
from fastapi import FastAPI

from ingestion.publisher import close_redis
from ingestion.repository import close_pool
from ingestion.router import router, _run_sync_for_provider
from ingestion.account_repository import list_accounts
from ingestion.schemas import EmailProvider

logger = structlog.get_logger()

SYNC_INTERVAL_SECONDS = 15 * 60  # 15 minutes


async def _periodic_sync() -> None:
    """Background task that syncs all connected providers every SYNC_INTERVAL_SECONDS."""
    await asyncio.sleep(60)  # Initial delay: let services settle after startup
    while True:
        try:
            accounts = await list_accounts()
            providers_synced: set[str] = set()
            for acct in accounts:
                prov = acct["provider"]
                if prov not in providers_synced:
                    providers_synced.add(prov)
                    try:
                        result = await _run_sync_for_provider(EmailProvider(prov))
                        logger.info("periodic sync completed", provider=prov, new=result.new_stored)
                    except Exception:
                        logger.exception("periodic sync failed", provider=prov)
        except Exception:
            logger.exception("periodic sync error")
        await asyncio.sleep(SYNC_INTERVAL_SECONDS)


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
    sync_task = asyncio.create_task(_periodic_sync())
    yield
    sync_task.cancel()
    await close_pool()
    await close_redis()
    logger.info("ingestion service stopped")


app = FastAPI(title="Ingestion Service", version="0.1.0", lifespan=lifespan)
app.include_router(router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
