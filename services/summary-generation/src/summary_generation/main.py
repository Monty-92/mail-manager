from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
import asyncio
from datetime import date, datetime, time, timezone

import structlog
from fastapi import FastAPI

from summary_generation.events import close_redis
from summary_generation.generator import generate_daily
from summary_generation.repository import close_pool
from summary_generation.router import router
from summary_generation.schemas import SummaryType

logger = structlog.get_logger()

MORNING_HOUR = 6
EVENING_HOUR = 18


def _seconds_until(target_hour: int) -> float:
    """Return seconds from now until the next occurrence of target_hour:00 UTC."""
    now = datetime.now(tz=timezone.utc)
    target = datetime.combine(now.date(), time(target_hour, 0), tzinfo=timezone.utc)
    if target <= now:
        from datetime import timedelta
        target += timedelta(days=1)
    return (target - now).total_seconds()


async def _scheduled_summaries() -> None:
    """Background task that generates morning and evening summaries at scheduled times."""
    await asyncio.sleep(30)  # Initial delay: let services settle
    while True:
        try:
            morning_wait = _seconds_until(MORNING_HOUR)
            evening_wait = _seconds_until(EVENING_HOUR)
            next_wait = min(morning_wait, evening_wait)
            summary_type = SummaryType.MORNING if morning_wait <= evening_wait else SummaryType.EVENING

            logger.info("next scheduled summary", type=summary_type.value, wait_seconds=int(next_wait))
            await asyncio.sleep(next_wait)

            today = date.today()
            try:
                result = await generate_daily(today, summary_type)
                logger.info(
                    "scheduled summary generated",
                    type=summary_type.value,
                    date=today.isoformat(),
                    emails=result.email_count,
                )
            except Exception:
                logger.exception("scheduled summary generation failed", type=summary_type.value)

        except asyncio.CancelledError:
            break
        except Exception:
            logger.exception("summary scheduler error")
            await asyncio.sleep(300)  # Wait 5 min before retrying on unexpected errors


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    structlog.configure(
        processors=[
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer(),
        ],
    )
    logger.info("summary-generation service started")
    scheduler_task = asyncio.create_task(_scheduled_summaries())
    yield
    scheduler_task.cancel()
    await close_pool()
    await close_redis()
    logger.info("summary-generation service stopped")


app = FastAPI(title="Summary Generation Service", version="0.1.0", lifespan=lifespan)
app.include_router(router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
