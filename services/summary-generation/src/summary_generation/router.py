"""FastAPI router for the summary generation service."""

from datetime import date

import structlog
from fastapi import APIRouter, HTTPException, Query

from summary_generation.events import publish_summary_generated
from summary_generation.generator import generate_daily, generate_thread
from summary_generation.repository import get_summary, get_summary_by_id, list_summaries
from summary_generation.schemas import Summary, SummaryListItem, SummaryResult, SummaryType

logger = structlog.get_logger()

router = APIRouter(prefix="/summaries", tags=["summaries"])


@router.get("", response_model=list[SummaryListItem])
async def list_all_summaries(limit: int = 30, offset: int = 0) -> list[SummaryListItem]:
    """List all summaries, ordered by most recent date."""
    return await list_summaries(limit=limit, offset=offset)


@router.get("/daily", response_model=Summary | None)
async def get_daily_summary(
    summary_type: SummaryType = Query(..., description="morning or evening"),
    target_date: date = Query(..., alias="date", description="Summary date (YYYY-MM-DD)"),
) -> Summary:
    """Get a specific daily summary by type and date."""
    summary = await get_summary(summary_type, target_date)
    if summary is None:
        raise HTTPException(status_code=404, detail="summary not found")
    return summary


@router.post("/daily", response_model=SummaryResult)
async def generate_daily_summary(
    summary_type: SummaryType = Query(..., description="morning or evening"),
    target_date: date = Query(..., alias="date", description="Summary date (YYYY-MM-DD)"),
) -> SummaryResult:
    """Generate (or regenerate) a daily summary for the given date and type."""
    result = await generate_daily(target_date, summary_type)
    if result.summary_id:
        await publish_summary_generated(result.summary_id, result.summary_type, str(result.date))
    return result


@router.post("/thread/{thread_id}")
async def summarize_thread(thread_id: str) -> dict[str, str]:
    """Generate an on-demand summary for an email thread."""
    markdown = await generate_thread(thread_id)
    if not markdown:
        raise HTTPException(status_code=404, detail="no emails found for thread")
    return {"thread_id": thread_id, "markdown": markdown}


@router.get("/{summary_id}", response_model=Summary)
async def get_summary_detail(summary_id: str) -> Summary:
    """Get a specific summary by ID."""
    summary = await get_summary_by_id(summary_id)
    if summary is None:
        raise HTTPException(status_code=404, detail="summary not found")
    return summary
