"""BFF router for LLM analysis endpoints."""

import structlog
from fastapi import APIRouter, HTTPException, Query

from bff.client import get_client
from bff.config import settings

logger = structlog.get_logger()

router = APIRouter(prefix="/api/v1/analyze", tags=["analysis"])


@router.get("/{email_id}")
async def get_analysis(email_id: str) -> dict:
    """Retrieve stored analysis for an email."""
    client = await get_client()
    resp = await client.get(f"{settings.llm_analysis_url}/analyze/{email_id}")
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.json().get("detail", "upstream error"))
    return resp.json()


@router.post("/batch")
async def analyze_batch(limit: int = Query(50)) -> dict:
    """Analyze up to N unanalyzed emails."""
    client = await get_client()
    resp = await client.post(f"{settings.llm_analysis_url}/analyze/batch", params={"limit": limit})
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.json().get("detail", "upstream error"))
    return resp.json()


@router.post("/{email_id}")
async def analyze_email(email_id: str) -> dict:
    """Analyze a single email on-demand."""
    client = await get_client()
    resp = await client.post(f"{settings.llm_analysis_url}/analyze/{email_id}")
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.json().get("detail", "upstream error"))
    return resp.json()
