"""BFF router for dashboard stats and pipeline health."""

from __future__ import annotations

import structlog
from fastapi import APIRouter

from bff.auth_repository import get_pool
from bff.client import get_client
from bff.config import settings

logger = structlog.get_logger()

router = APIRouter(prefix="/api/v1/stats", tags=["stats"])


@router.get("")
async def get_stats() -> dict:
    """Aggregate stats for the dashboard stat-cards.

    Returns email counts (total, today, unread), task counts (total, overdue,
    due_this_week, in_progress), and pipeline health (last event per stage).
    """
    pool = await get_pool()

    # ─── Email counts via DB view ───
    email_row = await pool.fetchrow(
        "SELECT total_emails, emails_today, unread_emails, preprocessed_emails, analyzed_emails FROM email_stats"
    )
    email_stats = dict(email_row) if email_row else {
        "total_emails": 0, "emails_today": 0, "unread_emails": 0,
        "preprocessed_emails": 0, "analyzed_emails": 0,
    }

    # ─── Task counts ───
    task_row = await pool.fetchrow(
        """
        SELECT
            COUNT(*) FILTER (WHERE status NOT IN ('done','cancelled'))           AS active,
            COUNT(*) FILTER (WHERE status NOT IN ('done','cancelled')
                             AND due_date < now())                               AS overdue,
            COUNT(*) FILTER (WHERE status NOT IN ('done','cancelled')
                             AND due_date BETWEEN now() AND now() + INTERVAL '7 days') AS due_this_week,
            COUNT(*) FILTER (WHERE status = 'in_progress')                       AS in_progress
        FROM tasks
        WHERE parent_task_id IS NULL
        """
    )
    task_stats = dict(task_row) if task_row else {
        "active": 0, "overdue": 0, "due_this_week": 0, "in_progress": 0,
    }

    # ─── Pipeline health: last event per stage ───
    pipeline_rows = await pool.fetch(
        """
        SELECT DISTINCT ON (stage) stage, occurred_at, details
        FROM pipeline_events
        ORDER BY stage, occurred_at DESC
        """
    )
    pipeline_health = {
        r["stage"]: {
            "last_event": r["occurred_at"].isoformat(),
            "details": dict(r["details"]) if r["details"] else {},
        }
        for r in pipeline_rows
    }

    return {
        "emails": {k: int(v) for k, v in email_stats.items()},
        "tasks": {k: int(v) for k, v in task_stats.items()},
        "pipeline": pipeline_health,
    }


@router.get("/pipeline")
async def get_pipeline_health() -> dict:
    """Return the last 20 pipeline events for the activity feed."""
    pool = await get_pool()
    rows = await pool.fetch(
        """
        SELECT id, stage, email_id, details, occurred_at
        FROM pipeline_events
        ORDER BY occurred_at DESC
        LIMIT 20
        """
    )
    return {
        "events": [
            {
                "id": str(r["id"]),
                "stage": r["stage"],
                "email_id": str(r["email_id"]) if r["email_id"] else None,
                "details": dict(r["details"]) if r["details"] else {},
                "occurred_at": r["occurred_at"].isoformat(),
            }
            for r in rows
        ]
    }
