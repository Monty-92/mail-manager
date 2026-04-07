"""BFF router for email ingestion endpoints."""

import structlog
from fastapi import APIRouter, HTTPException, Query

from bff.client import get_client
from bff.config import settings

logger = structlog.get_logger()

router = APIRouter(prefix="/api/v1/ingest", tags=["ingestion"])


@router.get("/auth/url/{provider}")
async def get_auth_url(provider: str) -> dict:
    """Get OAuth authorization URL for a provider."""
    client = await get_client()
    resp = await client.get(f"{settings.ingestion_url}/ingest/auth/url/{provider}")
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.json().get("detail", "upstream error"))
    return resp.json()


@router.post("/auth/callback")
async def auth_callback(body: dict) -> dict:
    """Exchange OAuth authorization code for tokens."""
    client = await get_client()
    resp = await client.post(f"{settings.ingestion_url}/ingest/auth/callback", json=body)
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.json().get("detail", "upstream error"))
    return resp.json()


@router.post("/sync/{provider}")
async def sync_provider(provider: str, max_results: int = Query(100)) -> dict:
    """Run incremental sync for a provider."""
    client = await get_client()
    resp = await client.post(
        f"{settings.ingestion_url}/ingest/sync/{provider}",
        params={"max_results": max_results},
    )
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.json().get("detail", "upstream error"))
    return resp.json()


@router.post("/fetch/{provider}")
async def fetch_provider(
    provider: str,
    max_results: int = Query(500),
    page_token: str | None = Query(None),
) -> dict:
    """Batch fetch full email history for a provider."""
    client = await get_client()
    params: dict = {"max_results": max_results}
    if page_token:
        params["page_token"] = page_token
    resp = await client.post(f"{settings.ingestion_url}/ingest/fetch/{provider}", params=params)
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.json().get("detail", "upstream error"))
    return resp.json()


@router.post("/resolve-labels/{provider}")
async def resolve_labels(provider: str) -> dict:
    """Translate stored provider label IDs to human-friendly names for all existing emails."""
    client = await get_client()
    resp = await client.post(f"{settings.ingestion_url}/ingest/resolve-labels/{provider}")
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.json().get("detail", "upstream error"))
    return resp.json()
