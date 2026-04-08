"""BFF router for user configuration (LLM model, sync toggles, etc.)."""

from __future__ import annotations

import asyncpg
import structlog
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from bff.auth_repository import get_pool

logger = structlog.get_logger()

router = APIRouter(prefix="/api/v1/settings", tags=["settings"])

# Keys that callers may read/write
_ALLOWED_KEYS = {
    "llm_model",
    "embed_model",
    "auto_sync",
    "auto_analyze",
    "default_calendar",
}


async def _get_config(pool: asyncpg.Pool) -> dict[str, str]:
    rows = await pool.fetch("SELECT key, value FROM user_config ORDER BY key")
    return {r["key"]: r["value"] for r in rows}


async def _set_config(pool: asyncpg.Pool, key: str, value: str) -> None:
    await pool.execute(
        """
        INSERT INTO user_config (key, value, updated_at) VALUES ($1, $2, now())
        ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = now()
        """,
        key,
        value,
    )


# ─── Endpoints ───


@router.get("")
async def get_all_settings() -> dict[str, str]:
    """Return all user config key-value pairs."""
    pool = await get_pool()
    return await _get_config(pool)


class SettingUpdate(BaseModel):
    value: str


@router.patch("/{key}")
async def update_setting(key: str, body: SettingUpdate) -> dict[str, str]:
    """Update a single user config key."""
    if key not in _ALLOWED_KEYS:
        raise HTTPException(status_code=400, detail=f"Unknown config key: {key}")
    pool = await get_pool()
    await _set_config(pool, key, body.value)
    logger.info("config updated", key=key)
    return {"key": key, "value": body.value}


@router.put("")
async def replace_settings(body: dict[str, str]) -> dict[str, str]:
    """Replace multiple settings at once. Unknown keys are rejected."""
    unknown = set(body.keys()) - _ALLOWED_KEYS
    if unknown:
        raise HTTPException(status_code=400, detail=f"Unknown config keys: {sorted(unknown)}")
    pool = await get_pool()
    for k, v in body.items():
        await _set_config(pool, k, v)
    logger.info("config bulk-updated", keys=list(body.keys()))
    return await _get_config(pool)
