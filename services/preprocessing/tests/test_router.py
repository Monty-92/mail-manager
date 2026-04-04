from unittest.mock import AsyncMock, patch

import pytest

from preprocessing.schemas import PreprocessingStatus, PreprocessResult


@pytest.mark.asyncio
async def test_health(client):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_preprocess_single_not_found(client):
    """POST /preprocess/{id} returns 404 when email not found."""
    mock_result = PreprocessResult(
        email_id="00000000-0000-0000-0000-000000000000",
        cleaned_text="",
        embedding_dim=0,
        status=PreprocessingStatus.FAILED,
        error="email not found",
    )
    with patch("preprocessing.router.preprocess_email", new_callable=AsyncMock, return_value=mock_result):
        response = await client.post("/preprocess/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404
    assert response.json()["detail"] == "email not found"


@pytest.mark.asyncio
async def test_preprocess_single_success(client):
    """POST /preprocess/{id} returns result on success."""
    mock_result = PreprocessResult(
        email_id="uuid-1",
        cleaned_text="clean text",
        embedding_dim=768,
        status=PreprocessingStatus.COMPLETED,
    )
    with patch("preprocessing.router.preprocess_email", new_callable=AsyncMock, return_value=mock_result):
        response = await client.post("/preprocess/uuid-1")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert data["embedding_dim"] == 768


@pytest.mark.asyncio
async def test_preprocess_batch(client):
    """POST /preprocess/batch returns list of results."""
    with patch("preprocessing.router.get_unprocessed_emails", new_callable=AsyncMock, return_value=[]):
        response = await client.post("/preprocess/batch?limit=5")
    assert response.status_code == 200
    assert response.json() == []
