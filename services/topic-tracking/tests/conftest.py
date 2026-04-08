from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

import topic_tracking.events as events_mod
import topic_tracking.repository as repo_mod
from topic_tracking.main import app


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
        patch("topic_tracking.main.subscribe_analyzed_emails", _noop_subscribe),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            yield ac
