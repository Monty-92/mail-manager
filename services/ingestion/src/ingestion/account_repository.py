"""Repository for connected_accounts table operations."""

from datetime import datetime

import asyncpg
import structlog

from ingestion.config import settings

logger = structlog.get_logger()

_pool: asyncpg.Pool | None = None


async def get_pool() -> asyncpg.Pool:
    """Get or create the connection pool (reuses the same DSN as the email repository)."""
    global _pool
    if _pool is None:
        dsn = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
        _pool = await asyncpg.create_pool(dsn, min_size=2, max_size=10)
        logger.info("account repository pool created")
    return _pool


async def close_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


async def list_accounts() -> list[dict]:
    """List all connected accounts."""
    pool = await get_pool()
    rows = await pool.fetch(
        "SELECT id, provider, email, display_name, scopes, created_at, updated_at FROM connected_accounts ORDER BY created_at"
    )
    return [dict(r) for r in rows]


async def get_account(account_id: str) -> dict | None:
    """Get a single account by ID (includes tokens)."""
    pool = await get_pool()
    row = await pool.fetchrow(
        "SELECT id, provider, email, display_name, access_token, refresh_token, token_expiry, scopes, created_at, updated_at "
        "FROM connected_accounts WHERE id = $1",
        account_id,
    )
    return dict(row) if row else None


async def get_accounts_by_provider(provider: str) -> list[dict]:
    """Get all accounts for a provider (includes tokens for sync)."""
    pool = await get_pool()
    rows = await pool.fetch(
        "SELECT id, provider, email, display_name, access_token, refresh_token, token_expiry, scopes "
        "FROM connected_accounts WHERE provider = $1 ORDER BY created_at",
        provider,
    )
    return [dict(r) for r in rows]


async def save_account(
    provider: str,
    email: str,
    display_name: str,
    access_token: str,
    refresh_token: str | None,
    token_expiry: datetime | None,
    scopes: list[str],
) -> dict:
    """Upsert a connected account. Returns the row."""
    pool = await get_pool()
    row = await pool.fetchrow(
        """
        INSERT INTO connected_accounts (provider, email, display_name, access_token, refresh_token, token_expiry, scopes)
        VALUES ($1, $2, $3, $4, $5, $6, $7)
        ON CONFLICT (provider, email) DO UPDATE SET
            display_name = EXCLUDED.display_name,
            access_token = EXCLUDED.access_token,
            refresh_token = COALESCE(EXCLUDED.refresh_token, connected_accounts.refresh_token),
            token_expiry = EXCLUDED.token_expiry,
            scopes = EXCLUDED.scopes,
            updated_at = now()
        RETURNING id, provider, email, display_name, scopes, created_at, updated_at
        """,
        provider,
        email,
        display_name,
        access_token,
        refresh_token,
        token_expiry,
        scopes,
    )
    return dict(row)


async def update_tokens(account_id: str, access_token: str, refresh_token: str | None, token_expiry: datetime | None) -> None:
    """Update just the tokens for an account (after refresh)."""
    pool = await get_pool()
    await pool.execute(
        """
        UPDATE connected_accounts
        SET access_token = $2, refresh_token = COALESCE($3, refresh_token), token_expiry = $4, updated_at = now()
        WHERE id = $1
        """,
        account_id,
        access_token,
        refresh_token,
        token_expiry,
    )


async def delete_account(account_id: str) -> bool:
    """Delete a connected account. Returns True if deleted."""
    pool = await get_pool()
    result = await pool.execute("DELETE FROM connected_accounts WHERE id = $1", account_id)
    return result == "DELETE 1"
