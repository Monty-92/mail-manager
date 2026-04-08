"""Google Tasks API client for bidirectional sync.

Scopes required: https://www.googleapis.com/auth/tasks
(already included in the Gmail OAuth flow SCOPES list in ingestion/providers/gmail.py)
"""

from __future__ import annotations

import structlog
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from task_management.schemas import Task, TaskStatus

logger = structlog.get_logger()

_DONE_STATUS = "completed"
_NEEDS_ACTION = "needsAction"


def _build_service(access_token: str, refresh_token: str | None, token_expiry_iso: str | None):
    """Build an authenticated Google Tasks service client."""
    creds = Credentials(
        token=access_token,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=None,  # populated from env when running inside ingestion; here tokens are pre-refreshed
        client_secret=None,
    )
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return build("tasks", "v1", credentials=creds, cache_discovery=False)


# ─── Task Lists ─────────────────────────────────────────────────────────────


def list_google_tasklists(service) -> list[dict]:
    """Return all Google Task Lists."""
    result = service.tasklists().list().execute()
    return result.get("items", [])


def create_google_tasklist(service, title: str) -> dict:
    """Create a new Google Task List and return the response."""
    return service.tasklists().insert(body={"title": title}).execute()


# ─── Tasks ──────────────────────────────────────────────────────────────────


def push_task_to_google(service, tasklist_id: str, task: Task) -> dict:
    """Create or update a task in Google Tasks.

    Returns the Google Tasks API response dict.
    """
    body: dict = {
        "title": task.title,
        "notes": task.notes or "",
        "status": _DONE_STATUS if task.status == TaskStatus.DONE else _NEEDS_ACTION,
    }
    if task.due_date:
        # Google Tasks due must be RFC 3339 date-only at midnight UTC
        body["due"] = task.due_date.strftime("%Y-%m-%dT00:00:00.000Z")

    if task.google_task_id:
        # Update existing task
        body["id"] = task.google_task_id
        return (
            service.tasks()
            .update(tasklist=tasklist_id, task=task.google_task_id, body=body)
            .execute()
        )
    else:
        # Create new task
        return service.tasks().insert(tasklist=tasklist_id, body=body).execute()


def fetch_google_tasks(service, tasklist_id: str, page_token: str | None = None) -> tuple[list[dict], str | None]:
    """Fetch all tasks from a Google Tasks list (handles pagination).

    Returns (tasks, next_page_token).
    """
    kwargs: dict = {"tasklist": tasklist_id, "showCompleted": True, "showHidden": True, "maxResults": 100}
    if page_token:
        kwargs["pageToken"] = page_token
    result = service.tasks().list(**kwargs).execute()
    return result.get("items", []), result.get("nextPageToken")


def delete_google_task(service, tasklist_id: str, google_task_id: str) -> None:
    """Delete a task from Google Tasks."""
    try:
        service.tasks().delete(tasklist=tasklist_id, task=google_task_id).execute()
    except HttpError as e:
        if e.resp.status != 404:
            raise
