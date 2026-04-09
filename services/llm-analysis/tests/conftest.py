from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

import llm_analysis.events as events_mod
import llm_analysis.repository as repo_mod
from llm_analysis.main import app


@pytest.fixture(autouse=True)
def mock_infrastructure():
    """Pre-set pool and Redis so the app lifespan never attempts real connections."""
    mock_pool = MagicMock()
    mock_pool.close = AsyncMock()
    mock_pool.fetch = AsyncMock(return_value=[])
    mock_pool.fetchrow = AsyncMock(return_value=None)
    mock_pool.execute = AsyncMock(return_value=None)
    mock_redis = MagicMock()
    mock_redis.aclose = AsyncMock()
    with (
        patch.object(repo_mod, "_pool", mock_pool),
        patch.object(events_mod, "_redis_client", mock_redis),
        patch("llm_analysis.main.subscribe_preprocessed_emails", AsyncMock()),
    ):
        yield


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
