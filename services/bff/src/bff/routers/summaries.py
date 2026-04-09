"""BFF router for summary generation endpoints."""

from datetime import date

import structlog
from fastapi import APIRouter, HTTPException, Query

from bff.client import get_client
from bff.config import settings

logger = structlog.get_logger()

router = APIRouter(prefix="/api/v1/summaries", tags=["summaries"])


@router.get("")
async def list_summaries(limit: int = Query(30), offset: int = Query(0)) -> list:
    """List all summaries ordered by most recent date."""
    client = await get_client()
    resp = await client.get(
        f"{settings.summary_generation_url}/summaries",
        params={"limit": limit, "offset": offset},
    )
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.json().get("detail", "upstream error"))
    return resp.json()


@router.get("/daily")
async def get_daily_summary(
    summary_type: str = Query(..., description="morning or evening"),
    target_date: date = Query(..., alias="date", description="Summary date (YYYY-MM-DD)"),
) -> dict:
    """Get a specific daily summary by type and date."""
    client = await get_client()
    resp = await client.get(
        f"{settings.summary_generation_url}/summaries/daily",
        params={"summary_type": summary_type, "date": str(target_date)},
    )
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.json().get("detail", "upstream error"))
    return resp.json()


@router.post("/daily")
async def generate_daily_summary(
    summary_type: str = Query(..., description="morning or evening"),
    target_date: date = Query(..., alias="date", description="Summary date (YYYY-MM-DD)"),
) -> dict:
    """Generate (or regenerate) a daily summary."""
    client = await get_client()
    resp = await client.post(
        f"{settings.summary_generation_url}/summaries/daily",
        params={"summary_type": summary_type, "date": str(target_date)},
    )
    if resp.status_code != 200:
        try:
            detail = resp.json().get("detail", "upstream error")
        except Exception:
            detail = resp.text or "upstream error"
        raise HTTPException(status_code=resp.status_code, detail=detail)
    return resp.json()


@router.post("/thread/{thread_id}")
async def summarize_thread(thread_id: str) -> dict:
    """Generate an on-demand summary for an email thread."""
    client = await get_client()
    resp = await client.post(f"{settings.summary_generation_url}/summaries/thread/{thread_id}")
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.json().get("detail", "upstream error"))
    return resp.json()


@router.get("/{summary_id}")
async def get_summary(summary_id: str) -> dict:
    """Get a specific summary by ID."""
    client = await get_client()
    resp = await client.get(f"{settings.summary_generation_url}/summaries/{summary_id}")
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.json().get("detail", "upstream error"))
    return resp.json()
