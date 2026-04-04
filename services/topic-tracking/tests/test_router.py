"""Tests for topic_tracking.router."""

from unittest.mock import AsyncMock, patch

import pytest

from topic_tracking.schemas import Topic, TopicMatch, TopicSnapshot, TopicSummary


_MOCK_TOPIC_SUMMARY = TopicSummary(id="t-1", name="Budget", email_count=3)
_MOCK_TOPIC = Topic(
    id="t-1",
    name="Budget",
    embedding=[0.1] * 768,
    snapshots=[TopicSnapshot(date="2026-04-04", email_count=3)],
    email_count=3,
)
_MOCK_MATCH = TopicMatch(topic_id="t-1", topic_name="Budget", similarity=1.0, is_new=False)


@pytest.mark.asyncio
async def test_list_topics(client):
    with patch("topic_tracking.router.list_topics", new_callable=AsyncMock, return_value=[_MOCK_TOPIC_SUMMARY]):
        response = await client.get("/topics")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "Budget"


@pytest.mark.asyncio
async def test_list_topics_empty(client):
    with patch("topic_tracking.router.list_topics", new_callable=AsyncMock, return_value=[]):
        response = await client.get("/topics")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_list_topics_with_params(client):
    with patch("topic_tracking.router.list_topics", new_callable=AsyncMock, return_value=[]) as mock:
        response = await client.get("/topics?limit=10&offset=5")
    assert response.status_code == 200
    mock.assert_called_once_with(limit=10, offset=5)


@pytest.mark.asyncio
async def test_get_email_topics(client):
    with patch(
        "topic_tracking.router.get_topics_for_email",
        new_callable=AsyncMock,
        return_value=[_MOCK_TOPIC_SUMMARY],
    ):
        response = await client.get("/topics/email/e-1")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == "t-1"


@pytest.mark.asyncio
async def test_get_email_topics_empty(client):
    with patch("topic_tracking.router.get_topics_for_email", new_callable=AsyncMock, return_value=[]):
        response = await client.get("/topics/email/e-99")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_assign_topics(client):
    with patch(
        "topic_tracking.router.assign_topics_for_email",
        new_callable=AsyncMock,
        return_value=[_MOCK_MATCH],
    ):
        response = await client.post("/topics/assign/e-1")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["topic_name"] == "Budget"
    assert data[0]["similarity"] == 1.0


@pytest.mark.asyncio
async def test_assign_topics_no_matches(client):
    with patch("topic_tracking.router.assign_topics_for_email", new_callable=AsyncMock, return_value=[]):
        response = await client.post("/topics/assign/e-1")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_get_topic(client):
    with patch("topic_tracking.router.get_topic_by_id", new_callable=AsyncMock, return_value=_MOCK_TOPIC):
        response = await client.get("/topics/t-1")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Budget"
    assert data["email_count"] == 3


@pytest.mark.asyncio
async def test_get_topic_not_found(client):
    with patch("topic_tracking.router.get_topic_by_id", new_callable=AsyncMock, return_value=None):
        response = await client.get("/topics/nonexistent")
    assert response.status_code == 404
    assert response.json()["detail"] == "topic not found"


@pytest.mark.asyncio
async def test_delete_topic(client):
    with patch("topic_tracking.router.delete_topic", new_callable=AsyncMock, return_value=True):
        response = await client.delete("/topics/t-1")
    assert response.status_code == 204


@pytest.mark.asyncio
async def test_delete_topic_not_found(client):
    with patch("topic_tracking.router.delete_topic", new_callable=AsyncMock, return_value=False):
        response = await client.delete("/topics/nonexistent")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_topic_emails(client):
    with patch(
        "topic_tracking.router.get_email_ids_for_topic",
        new_callable=AsyncMock,
        return_value=["e-1", "e-2"],
    ):
        response = await client.get("/topics/t-1/emails")
    assert response.status_code == 200
    assert response.json() == ["e-1", "e-2"]


@pytest.mark.asyncio
async def test_get_topic_emails_empty(client):
    with patch("topic_tracking.router.get_email_ids_for_topic", new_callable=AsyncMock, return_value=[]):
        response = await client.get("/topics/t-1/emails")
    assert response.status_code == 200
    assert response.json() == []
