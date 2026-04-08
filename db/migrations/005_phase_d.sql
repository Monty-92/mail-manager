-- mail-manager: Phase D additions
-- Adds user_config table for LLM/sync preferences,
-- google_tasks_account_id on tasks for calendar assignment,
-- and pipeline_health view for E2E monitoring.

-- ─── user_config ───
-- Key/value store for user-controlled settings.
-- Values are TEXT; callers cast as needed.
CREATE TABLE IF NOT EXISTS user_config (
    key         TEXT PRIMARY KEY,
    value       TEXT NOT NULL,
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Seed sensible defaults (INSERT … ON CONFLICT DO NOTHING keeps idempotent reruns safe)
INSERT INTO user_config (key, value) VALUES
    ('llm_model',          'llama3.1:8b'),
    ('embed_model',        'nomic-embed-text'),
    ('auto_sync',          'true'),
    ('auto_analyze',       'true'),
    ('default_calendar',   '')          -- set to first account id on first connect
ON CONFLICT (key) DO NOTHING;

-- ─── task_calendar_account_id ───
-- Nullable FK to the connected_account used when pushing a task to Google Tasks.
-- NULL = use default calendar from user_config.
ALTER TABLE tasks
    ADD COLUMN IF NOT EXISTS calendar_account_id UUID REFERENCES connected_accounts(id) ON DELETE SET NULL;

-- ─── pipeline_events ───
-- Append-only audit log of pipeline stage completions.
-- Used by the /health/pipeline endpoint to show E2E status without redis coupling.
CREATE TABLE IF NOT EXISTS pipeline_events (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    stage       TEXT NOT NULL CHECK (stage IN ('ingested','preprocessed','analyzed','topics_assigned','tasks_extracted','google_tasks_synced')),
    email_id    UUID REFERENCES emails(id) ON DELETE CASCADE,
    details     JSONB NOT NULL DEFAULT '{}',
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_pipeline_events_stage      ON pipeline_events (stage);
CREATE INDEX IF NOT EXISTS idx_pipeline_events_email_id   ON pipeline_events (email_id);
CREATE INDEX IF NOT EXISTS idx_pipeline_events_occurred_at ON pipeline_events (occurred_at DESC);

-- ─── email_stats view ───
-- Cheap daily/total counts for the dashboard stat-cards.
CREATE OR REPLACE VIEW email_stats AS
SELECT
    COUNT(*)                                                            AS total_emails,
    COUNT(*) FILTER (WHERE received_at::date = CURRENT_DATE)           AS emails_today,
    COUNT(*) FILTER (WHERE 'UNREAD' = ANY(labels))                     AS unread_emails,
    COUNT(*) FILTER (WHERE embedding IS NOT NULL)                      AS preprocessed_emails,
    COUNT(*) FILTER (
        WHERE id IN (SELECT DISTINCT email_id FROM email_analyses)
    )                                                                   AS analyzed_emails
FROM emails;
