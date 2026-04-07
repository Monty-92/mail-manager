"""Tests for new ingestion email endpoints: labels, label filter, email detail with html_body."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from ingestion.main import app
from ingestion.schemas import EmailProvider, StoredEmail


def _make_stored_email(**overrides) -> StoredEmail:
    defaults = dict(
        id="aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
        provider=EmailProvider.GMAIL,
        external_id="ext-1",
        thread_id="thread-1",
        sender="alice@example.com",
        recipients=["bob@example.com"],
        subject="Test Subject",
        received_at=datetime(2024, 6, 1, tzinfo=timezone.utc),
        labels=["INBOX", "IMPORTANT"],
        markdown_body="# Hello",
        html_body="<h1>Hello</h1>",
        created_at=datetime(2024, 6, 1, 0, 1, tzinfo=timezone.utc),
    )
    defaults.update(overrides)
    return StoredEmail(**defaults)


# ─── GET /ingest/emails/labels ───


@pytest.mark.asyncio
async def test_get_labels_returns_list():
    """GET /ingest/emails/labels returns distinct label list."""
    with patch("ingestion.router.get_distinct_labels", new_callable=AsyncMock) as mock_labels:
        mock_labels.return_value = ["INBOX", "IMPORTANT", "Work/Projects"]
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/ingest/emails/labels")
    assert response.status_code == 200
    assert response.json() == ["INBOX", "IMPORTANT", "Work/Projects"]


@pytest.mark.asyncio
async def test_get_labels_empty():
    """GET /ingest/emails/labels returns empty list when no labels exist."""
    with patch("ingestion.router.get_distinct_labels", new_callable=AsyncMock) as mock_labels:
        mock_labels.return_value = []
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/ingest/emails/labels")
    assert response.status_code == 200
    assert response.json() == []


# ─── GET /ingest/emails with label filter ───


@pytest.mark.asyncio
async def test_get_emails_with_label_filter():
    """GET /ingest/emails?label=INBOX passes label to list_emails."""
    email = _make_stored_email()
    with patch("ingestion.router.list_emails", new_callable=AsyncMock) as mock_list:
        mock_list.return_value = ([email], 1)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/ingest/emails", params={"label": "INBOX"})
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert len(data["emails"]) == 1
    # Verify label was passed through to repository function
    mock_list.assert_called_once_with(limit=50, offset=0, provider=None, search=None, label="INBOX")


@pytest.mark.asyncio
async def test_get_emails_without_label():
    """GET /ingest/emails without label passes label=None."""
    with patch("ingestion.router.list_emails", new_callable=AsyncMock) as mock_list:
        mock_list.return_value = ([], 0)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/ingest/emails")
    assert response.status_code == 200
    mock_list.assert_called_once_with(limit=50, offset=0, provider=None, search=None, label=None)


@pytest.mark.asyncio
async def test_get_emails_with_combined_filters():
    """GET /ingest/emails with provider + label + search passes all through."""
    with patch("ingestion.router.list_emails", new_callable=AsyncMock) as mock_list:
        mock_list.return_value = ([], 0)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(
                "/ingest/emails", params={"provider": "gmail", "label": "Work", "search": "invoice", "limit": 10}
            )
    assert response.status_code == 200
    mock_list.assert_called_once_with(limit=10, offset=0, provider="gmail", search="invoice", label="Work")


# ─── GET /ingest/emails/{email_id} ───


@pytest.mark.asyncio
async def test_get_email_by_id_includes_html_body():
    """GET /ingest/emails/{id} returns email with html_body field."""
    email = _make_stored_email(html_body="<div>Rich HTML content</div>")
    with patch("ingestion.router.get_email_by_id", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = email
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(f"/ingest/emails/{email.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["html_body"] == "<div>Rich HTML content</div>"
    assert data["markdown_body"] == "# Hello"


@pytest.mark.asyncio
async def test_get_email_by_id_empty_html_body():
    """GET /ingest/emails/{id} returns empty html_body when none was stored."""
    email = _make_stored_email(html_body="")
    with patch("ingestion.router.get_email_by_id", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = email
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(f"/ingest/emails/{email.id}")
    assert response.status_code == 200
    assert response.json()["html_body"] == ""


@pytest.mark.asyncio
async def test_get_email_not_found():
    """GET /ingest/emails/{id} returns 404 for unknown email."""
    with patch("ingestion.router.get_email_by_id", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = None
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/ingest/emails/nonexistent-uuid")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()
