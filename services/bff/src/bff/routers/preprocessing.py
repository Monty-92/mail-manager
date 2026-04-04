"""BFF router for preprocessing endpoints."""

import structlog
from fastapi import APIRouter, HTTPException, Query

from bff.client import get_client
from bff.config import settings

logger = structlog.get_logger()

router = APIRouter(prefix="/api/v1/preprocess", tags=["preprocessing"])


@router.post("/batch")
async def preprocess_batch(limit: int = Query(50)) -> dict:
    """Preprocess up to N unprocessed emails."""
    client = await get_client()
    resp = await client.post(f"{settings.preprocessing_url}/preprocess/batch", params={"limit": limit})
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.json().get("detail", "upstream error"))
    return resp.json()


@router.post("/{email_id}")
async def preprocess_email(email_id: str) -> dict:
    """Preprocess a single email on-demand."""
    client = await get_client()
    resp = await client.post(f"{settings.preprocessing_url}/preprocess/{email_id}")
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.json().get("detail", "upstream error"))
    return resp.json()
