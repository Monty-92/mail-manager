"""BFF router for connected account management (proxy to ingestion service)."""

import asyncio
from uuid import UUID

import httpx
import structlog
from fastapi import APIRouter, HTTPException, Query

from bff.client import get_client
from bff.config import settings

logger = structlog.get_logger()

router = APIRouter(prefix="/api/v1/accounts", tags=["accounts"])

MAX_RETRIES = 2
RETRY_DELAY = 1.0


def _extract_detail(resp: httpx.Response) -> str:
    """Extract error detail from an upstream response, handling non-JSON bodies."""
    try:
        return resp.json().get("detail", f"Upstream error (HTTP {resp.status_code})")
    except Exception:
        return resp.text or f"Upstream error (HTTP {resp.status_code})"


@router.get("")
async def list_accounts() -> list[dict]:
    """List all connected accounts."""
    client = await get_client()
    last_exc: Exception | None = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = await client.get(f"{settings.ingestion_url}/ingest/accounts")
            if resp.status_code != 200:
                raise HTTPException(status_code=resp.status_code, detail=_extract_detail(resp))
            return resp.json()
        except httpx.TimeoutException as exc:
            last_exc = exc
            logger.warning("upstream timeout, retrying", attempt=attempt, url="/ingest/accounts")
            if attempt < MAX_RETRIES:
                await asyncio.sleep(RETRY_DELAY)
    raise HTTPException(status_code=504, detail="Upstream service timed out")


@router.delete("/{account_id}")
async def disconnect_account(account_id: UUID) -> dict:
    """Disconnect a connected account."""
    client = await get_client()
    resp = await client.delete(f"{settings.ingestion_url}/ingest/accounts/{account_id}")
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=_extract_detail(resp))
    return resp.json()


@router.get("/auth/url/{provider}")
async def get_auth_url(provider: str) -> dict:
    """Get OAuth authorization URL for a provider."""
    client = await get_client()
    resp = await client.get(f"{settings.ingestion_url}/ingest/auth/url/{provider}")
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=_extract_detail(resp))
    return resp.json()


@router.post("/auth/callback")
async def auth_callback(body: dict) -> dict:
    """Exchange OAuth authorization code for tokens."""
    client = await get_client()
    resp = await client.post(f"{settings.ingestion_url}/ingest/auth/callback", json=body)
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=_extract_detail(resp))
    return resp.json()


@router.post("/auth/device/{provider}")
async def start_device_flow(provider: str) -> dict:
    """Start OAuth device authorization flow."""
    client = await get_client()
    resp = await client.post(f"{settings.ingestion_url}/ingest/auth/device/{provider}")
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=_extract_detail(resp))
    return resp.json()


@router.post("/auth/device/{provider}/poll")
async def poll_device_flow(provider: str, device_code: str = Query(...)) -> dict:
    """Poll device authorization flow status."""
    client = await get_client()
    resp = await client.post(
        f"{settings.ingestion_url}/ingest/auth/device/{provider}/poll",
        params={"device_code": device_code},
    )
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=_extract_detail(resp))
    return resp.json()
