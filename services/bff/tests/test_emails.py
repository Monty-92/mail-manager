"""Tests for BFF emails router: label passthrough, labels endpoint, email detail."""

from unittest.mock import AsyncMock, patch

import httpx
import pytest


def _mock_response(status_code: int = 200, json_data: dict | list | None = None) -> httpx.Response:
    return httpx.Response(status_code=status_code, json=json_data if json_data is not None else {})


# ─── GET /api/v1/emails/labels ───


@pytest.mark.asyncio
async def test_list_labels(client):
    """GET /api/v1/emails/labels proxies to ingestion and returns label list."""
    with patch("bff.routers.emails.get_client", new_callable=AsyncMock) as mock_get:
        mock_http = AsyncMock()
        mock_http.get.return_value = _mock_response(200, ["INBOX", "IMPORTANT", "Work/Projects"])
        mock_get.return_value = mock_http
        response = await client.get("/api/v1/emails/labels")
    assert response.status_code == 200
    assert response.json() == ["INBOX", "IMPORTANT", "Work/Projects"]


@pytest.mark.asyncio
async def test_list_labels_empty(client):
    """GET /api/v1/emails/labels returns empty list when no labels."""
    with patch("bff.routers.emails.get_client", new_callable=AsyncMock) as mock_get:
        mock_http = AsyncMock()
        mock_http.get.return_value = _mock_response(200, [])
        mock_get.return_value = mock_http
        response = await client.get("/api/v1/emails/labels")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_list_labels_upstream_error(client):
    """GET /api/v1/emails/labels passes through upstream errors."""
    with patch("bff.routers.emails.get_client", new_callable=AsyncMock) as mock_get:
        mock_http = AsyncMock()
        mock_http.get.return_value = _mock_response(500, {"detail": "db connection failed"})
        mock_get.return_value = mock_http
        response = await client.get("/api/v1/emails/labels")
    assert response.status_code == 500


# ─── GET /api/v1/emails with label filter ───


@pytest.mark.asyncio
async def test_list_emails_with_label(client):
    """GET /api/v1/emails?label=INBOX passes label param to ingestion."""
    with patch("bff.routers.emails.get_client", new_callable=AsyncMock) as mock_get:
        mock_http = AsyncMock()
        mock_http.get.return_value = _mock_response(200, {"emails": [], "total": 0, "limit": 50, "offset": 0})
        mock_get.return_value = mock_http
        response = await client.get("/api/v1/emails?label=INBOX")
    assert response.status_code == 200
    # Verify label was included in the upstream request params
    call_kwargs = mock_http.get.call_args
    params = call_kwargs.kwargs.get("params") or call_kwargs[1].get("params", {})
    assert params["label"] == "INBOX"


@pytest.mark.asyncio
async def test_list_emails_without_label(client):
    """GET /api/v1/emails without label does not include label param."""
    with patch("bff.routers.emails.get_client", new_callable=AsyncMock) as mock_get:
        mock_http = AsyncMock()
        mock_http.get.return_value = _mock_response(200, {"emails": [], "total": 0, "limit": 50, "offset": 0})
        mock_get.return_value = mock_http
        response = await client.get("/api/v1/emails")
    assert response.status_code == 200
    call_kwargs = mock_http.get.call_args
    params = call_kwargs.kwargs.get("params") or call_kwargs[1].get("params", {})
    assert "label" not in params


@pytest.mark.asyncio
async def test_list_emails_with_all_filters(client):
    """GET /api/v1/emails with provider + label + search passes all params."""
    with patch("bff.routers.emails.get_client", new_callable=AsyncMock) as mock_get:
        mock_http = AsyncMock()
        mock_http.get.return_value = _mock_response(200, {"emails": [], "total": 0, "limit": 10, "offset": 0})
        mock_get.return_value = mock_http
        response = await client.get("/api/v1/emails?provider=gmail&label=Work&search=invoice&limit=10")
    assert response.status_code == 200
    call_kwargs = mock_http.get.call_args
    params = call_kwargs.kwargs.get("params") or call_kwargs[1].get("params", {})
    assert params["provider"] == "gmail"
    assert params["label"] == "Work"
    assert params["search"] == "invoice"
    assert params["limit"] == 10


# ─── GET /api/v1/emails/{email_id} ───


@pytest.mark.asyncio
async def test_get_email_returns_html_body(client):
    """GET /api/v1/emails/{id} returns email data including html_body."""
    email_data = {
        "id": "e-1",
        "subject": "Test",
        "html_body": "<p>Rich content</p>",
        "markdown_body": "# Rich content",
    }
    with patch("bff.routers.emails.get_client", new_callable=AsyncMock) as mock_get:
        mock_http = AsyncMock()
        mock_http.get.return_value = _mock_response(200, email_data)
        mock_get.return_value = mock_http
        response = await client.get("/api/v1/emails/e-1")
    assert response.status_code == 200
    data = response.json()
    assert data["html_body"] == "<p>Rich content</p>"
    assert data["markdown_body"] == "# Rich content"


@pytest.mark.asyncio
async def test_get_email_not_found(client):
    """GET /api/v1/emails/{id} returns 404 from upstream."""
    with patch("bff.routers.emails.get_client", new_callable=AsyncMock) as mock_get:
        mock_http = AsyncMock()
        mock_http.get.return_value = _mock_response(404, {"detail": "Email not found"})
        mock_get.return_value = mock_http
        response = await client.get("/api/v1/emails/nonexistent")
    assert response.status_code == 404
