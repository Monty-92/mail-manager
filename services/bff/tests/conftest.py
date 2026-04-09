from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import jwt
import pytest
from httpx import ASGITransport, AsyncClient

import bff.auth_repository as auth_repo_mod
from bff.config import settings
from bff.main import app

# 32-byte test secret avoids InsecureKeyLengthWarning from PyJWT
_TEST_JWT_SECRET = "test-jwt-secret-32-bytes-longXXX"


def _make_test_token() -> str:
    """Create a valid JWT for testing using the test secret."""
    payload = {
        "sub": "test-user-id",
        "username": "testuser",
        "exp": datetime.now(tz=timezone.utc) + timedelta(hours=1),
    }
    return jwt.encode(payload, _TEST_JWT_SECRET, algorithm="HS256")


@pytest.fixture(autouse=True)
def mock_infrastructure():
    """Pre-set DB pool and JWT secret so the app lifespan never attempts real connections."""
    mock_pool = MagicMock()
    mock_pool.close = AsyncMock()
    mock_pool.fetch = AsyncMock(return_value=[])
    mock_pool.fetchrow = AsyncMock(return_value=None)
    mock_pool.execute = AsyncMock(return_value=None)
    with (
        patch.object(auth_repo_mod, "_pool", mock_pool),
        patch.object(settings, "jwt_secret", _TEST_JWT_SECRET),
    ):
        yield


@pytest.fixture
async def client():
    token = _make_test_token()
    headers = {"Authorization": f"Bearer {token}"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test", headers=headers) as ac:
        yield ac
