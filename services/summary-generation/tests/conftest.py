from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

import summary_generation.events as events_mod
import summary_generation.repository as repo_mod
from summary_generation.main import app


def _make_mock_pool() -> MagicMock:
    pool = MagicMock()
    pool.close = AsyncMock()
    pool.fetch = AsyncMock(return_value=[])
    pool.fetchrow = AsyncMock(return_value=None)
    pool.execute = AsyncMock(return_value=None)
    return pool


@pytest.fixture(autouse=True)
def mock_infrastructure():
    """Pre-set module-level globals so the app lifespan never attempts real connections."""
    mock_redis = MagicMock()
    mock_redis.aclose = AsyncMock()
    with (
        patch.object(repo_mod, "_pool", _make_mock_pool()),
        patch.object(events_mod, "_redis_client", mock_redis),
    ):
        yield


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
