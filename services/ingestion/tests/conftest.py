from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

import ingestion.account_repository as account_repo_mod
import ingestion.publisher as publisher_mod
import ingestion.repository as repo_mod
from ingestion.main import app


def _make_mock_pool() -> MagicMock:
    pool = MagicMock()
    pool.close = AsyncMock()
    pool.fetch = AsyncMock(return_value=[])
    pool.fetchrow = AsyncMock(return_value=None)
    pool.execute = AsyncMock(return_value=None)
    return pool


@pytest.fixture(autouse=True)
def mock_infrastructure():
    """Pre-set pools and Redis so the app lifespan never attempts real connections."""
    mock_redis = MagicMock()
    mock_redis.aclose = AsyncMock()
    with (
        patch.object(repo_mod, "_pool", _make_mock_pool()),
        patch.object(account_repo_mod, "_pool", _make_mock_pool()),
        patch.object(publisher_mod, "_redis_client", mock_redis),
    ):
        yield


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
