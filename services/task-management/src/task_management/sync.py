"""Bidirectional Google Tasks sync orchestrator."""

from __future__ import annotations

from datetime import datetime, timezone

import asyncpg
import structlog

from task_management.google_tasks import (
    _build_service,
    _DONE_STATUS,
    create_google_tasklist,
    delete_google_task,
    fetch_google_tasks,
    list_google_tasklists,
    push_task_to_google,
)
from task_management.repository import (
    get_pool,
    get_task_by_id,
    list_tasks,
    update_task,
)
from task_management.schemas import Task, TaskStatus, TaskUpdate

logger = structlog.get_logger()


async def _get_accounts(pool: asyncpg.Pool, account_id: str | None = None) -> list[dict]:
    """Return Gmail connected accounts that have the tasks scope."""
    if account_id:
        rows = await pool.fetch(
            "SELECT id, access_token, refresh_token, token_expiry FROM connected_accounts WHERE id = $1 AND provider = 'gmail'",
            account_id,
        )
    else:
        rows = await pool.fetch(
            "SELECT id, access_token, refresh_token, token_expiry FROM connected_accounts WHERE provider = 'gmail'"
        )
    return [dict(r) for r in rows]


async def _record_google_task_id(pool: asyncpg.Pool, task_id: str, google_task_id: str, tasklist_id: str) -> None:
    await pool.execute(
        "UPDATE tasks SET google_task_id = $1, last_synced_at = now(), updated_at = now() WHERE id = $2",
        google_task_id,
        task_id,
    )


async def _ensure_tasklist(service, pool: asyncpg.Pool, list_name: str, existing_google_id: str | None) -> str:
    """Return google_tasklist_id for the given task list, creating it remotely if needed.
    Updates task_lists.google_tasklist_id if it changed.
    """
    if existing_google_id:
        return existing_google_id

    # Create a new Google Task List matching our local list name
    remote = create_google_tasklist(service, list_name)
    remote_id: str = remote["id"]
    # Persist the mapping
    await pool.execute(
        "UPDATE task_lists SET google_tasklist_id = $1, updated_at = now() WHERE name = $2",
        remote_id,
        list_name,
    )
    return remote_id


async def push_tasks_to_google(account_id: str | None = None) -> dict:
    """Push all un-synced (or dirty) local tasks to Google Tasks.

    Returns a summary dict: {pushed: int, failed: int}.
    """
    pool = await get_pool()
    accounts = await _get_accounts(pool, account_id)
    if not accounts:
        logger.warning("no gmail accounts found for google tasks sync")
        return {"pushed": 0, "failed": 0, "error": "no_accounts"}

    # Use the first account (or the requested one)
    acct = accounts[0]
    service = _build_service(
        acct["access_token"],
        acct.get("refresh_token"),
        str(acct["token_expiry"]) if acct.get("token_expiry") else None,
    )

    # Fetch or create remote task lists
    remote_lists = {r["title"]: r["id"] for r in list_google_tasklists(service)}
    local_lists = await pool.fetch(
        "SELECT id, name, google_tasklist_id FROM task_lists ORDER BY position"
    )

    list_id_to_google: dict[str, str] = {}
    for local in local_lists:
        gid = local["google_tasklist_id"] or remote_lists.get(local["name"])
        if not gid:
            remote = create_google_tasklist(service, local["name"])
            gid = remote["id"]
            await pool.execute(
                "UPDATE task_lists SET google_tasklist_id = $1, updated_at = now() WHERE id = $2",
                gid,
                str(local["id"]),
            )
        list_id_to_google[str(local["id"])] = gid

    # Tasks that need syncing: no google_task_id, or updated_at > last_synced_at
    rows = await pool.fetch(
        """
        SELECT id, title, notes, status, priority, due_date, list_id, google_task_id, last_synced_at, parent_task_id
        FROM tasks
        WHERE parent_task_id IS NULL
          AND (google_task_id IS NULL OR updated_at > COALESCE(last_synced_at, '1970-01-01'))
        ORDER BY created_at
        """
    )

    pushed = failed = 0
    for row in rows:
        task_id = str(row["id"])
        list_id = str(row["list_id"]) if row["list_id"] else None
        # Determine which Google tasklist to use
        if list_id and list_id in list_id_to_google:
            gtasklist_id = list_id_to_google[list_id]
        else:
            # Use "@default" as fallback
            gtasklist_id = "@default"

        task = await get_task_by_id(task_id)
        if not task:
            continue
        try:
            result = push_task_to_google(service, gtasklist_id, task)
            await _record_google_task_id(pool, task_id, result["id"], gtasklist_id)
            pushed += 1
            logger.debug("task pushed to google", task_id=task_id, google_id=result["id"])
        except Exception as exc:
            logger.error("failed to push task", task_id=task_id, error=str(exc))
            failed += 1

    logger.info("google tasks push complete", pushed=pushed, failed=failed)
    return {"pushed": pushed, "failed": failed}


async def pull_tasks_from_google(account_id: str | None = None) -> dict:
    """Pull task status/completion changes back from Google Tasks.

    Returns a summary dict: {updated: int, failed: int}.
    """
    pool = await get_pool()
    accounts = await _get_accounts(pool, account_id)
    if not accounts:
        return {"updated": 0, "failed": 0, "error": "no_accounts"}

    acct = accounts[0]
    service = _build_service(
        acct["access_token"],
        acct.get("refresh_token"),
        str(acct["token_expiry"]) if acct.get("token_expiry") else None,
    )

    # Only look at lists we know about
    local_lists = await pool.fetch(
        "SELECT id, google_tasklist_id FROM task_lists WHERE google_tasklist_id IS NOT NULL"
    )

    updated = failed = 0
    for local in local_lists:
        gtasklist_id: str = local["google_tasklist_id"]
        page_token = None
        while True:
            try:
                items, page_token = fetch_google_tasks(service, gtasklist_id, page_token)
            except Exception as exc:
                logger.error("failed to fetch google tasks", tasklist=gtasklist_id, error=str(exc))
                failed += 1
                break

            for item in items:
                google_id = item.get("id")
                if not google_id:
                    continue
                # Find matching local task
                row = await pool.fetchrow(
                    "SELECT id, status FROM tasks WHERE google_task_id = $1", google_id
                )
                if not row:
                    continue
                # Map Google status → local status
                remote_done = item.get("status") == _DONE_STATUS
                local_done = row["status"] == TaskStatus.DONE.value
                if remote_done != local_done:
                    new_status = TaskStatus.DONE if remote_done else TaskStatus.PENDING
                    try:
                        await pool.execute(
                            "UPDATE tasks SET status = $1, updated_at = now(), last_synced_at = now() WHERE id = $2",
                            new_status.value,
                            str(row["id"]),
                        )
                        updated += 1
                    except Exception as exc:
                        logger.error("failed to update local task", error=str(exc))
                        failed += 1

            if not page_token:
                break

    logger.info("google tasks pull complete", updated=updated, failed=failed)
    return {"updated": updated, "failed": failed}
