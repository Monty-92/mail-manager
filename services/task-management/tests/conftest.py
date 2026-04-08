from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

import task_management.events as events_mod
import task_management.repository as repo_mod
from task_management.main import app


@pytest.fixture
async def client():
    mock_pool = MagicMock()
    mock_pool.close = AsyncMock()
    mock_redis = MagicMock()
    mock_redis.aclose = AsyncMock()

    async def _noop_subscribe(callback):
        pass

    with (
        patch.object(repo_mod, "_pool", mock_pool),
        patch.object(events_mod, "_redis_client", mock_redis),
        patch("task_management.main.subscribe_analyzed_emails", _noop_subscribe),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            yield ac
