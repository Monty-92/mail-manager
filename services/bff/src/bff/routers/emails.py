"""BFF router for email browsing endpoints."""

import structlog
from fastapi import APIRouter, HTTPException, Query

from bff.client import get_client
from bff.config import settings

logger = structlog.get_logger()

router = APIRouter(prefix="/api/v1/emails", tags=["emails"])


@router.get("")
async def list_emails(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    provider: str | None = Query(None),
    search: str | None = Query(None),
    label: str | None = Query(None),
) -> dict:
    """List stored emails with pagination and filtering."""
    client = await get_client()
    params: dict[str, str | int] = {"limit": limit, "offset": offset}
    if provider:
        params["provider"] = provider
    if search:
        params["search"] = search
    if label:
        params["label"] = label
    resp = await client.get(f"{settings.ingestion_url}/ingest/emails", params=params)
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    return resp.json()


@router.get("/labels")
async def list_labels() -> list[str]:
    """Get all distinct email labels."""
    client = await get_client()
    resp = await client.get(f"{settings.ingestion_url}/ingest/emails/labels")
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    return resp.json()


@router.get("/{email_id}")
async def get_email(email_id: str) -> dict:
    """Get a single email by ID."""
    client = await get_client()
    resp = await client.get(f"{settings.ingestion_url}/ingest/emails/{email_id}")
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    return resp.json()
