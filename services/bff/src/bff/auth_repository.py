"""Repository for app_user table operations."""

from datetime import datetime

import asyncpg
import structlog

logger = structlog.get_logger()

_pool: asyncpg.Pool | None = None


async def get_pool() -> asyncpg.Pool:
    """Get or create the connection pool."""
    global _pool
    if _pool is None:
        from bff.config import settings

        dsn = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
        _pool = await asyncpg.create_pool(dsn, min_size=2, max_size=10)
        logger.info("bff auth database pool created")
    return _pool


async def close_pool() -> None:
    """Close the connection pool."""
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


async def get_user_count() -> int:
    """Return total number of users (for setup-status check)."""
    pool = await get_pool()
    row = await pool.fetchrow("SELECT count(*) AS cnt FROM app_user")
    return row["cnt"] if row else 0


async def get_user_by_username(username: str) -> dict | None:
    """Fetch a user row by username."""
    pool = await get_pool()
    row = await pool.fetchrow(
        "SELECT id, username, password_hash, totp_secret, is_setup_complete, created_at FROM app_user WHERE username = $1",
        username,
    )
    if row is None:
        return None
    return dict(row)


async def create_user(username: str, password_hash: str, totp_secret: str) -> dict:
    """Insert a new user and return the row."""
    pool = await get_pool()
    row = await pool.fetchrow(
        """
        INSERT INTO app_user (username, password_hash, totp_secret, is_setup_complete)
        VALUES ($1, $2, $3, true)
        RETURNING id, username, password_hash, totp_secret, is_setup_complete, created_at
        """,
        username,
        password_hash,
        totp_secret,
    )
    return dict(row)
