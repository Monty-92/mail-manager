from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

import summary_generation.events as events_mod
import summary_generation.repository as repo_mod
from summary_generation.main import app


@pytest.fixture
async def client():
    mock_pool = MagicMock()
    mock_pool.close = AsyncMock()
    mock_redis = MagicMock()
    mock_redis.aclose = AsyncMock()

    with (
        patch.object(repo_mod, "_pool", mock_pool),
        patch.object(events_mod, "_redis_client", mock_redis),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            yield ac
