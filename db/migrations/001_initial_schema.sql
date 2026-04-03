-- mail-manager: Initial Database Schema
-- Requires PostgreSQL 16+ with pgvector extension

-- ─── Extensions ───
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "vector";

-- ─── emails ───
CREATE TABLE IF NOT EXISTS emails (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    provider        TEXT NOT NULL CHECK (provider IN ('gmail', 'outlook')),
    external_id     TEXT NOT NULL,
    thread_id       TEXT,
    sender          TEXT NOT NULL,
    recipients      TEXT[] NOT NULL DEFAULT '{}',
    subject         TEXT NOT NULL DEFAULT '',
    received_at     TIMESTAMPTZ NOT NULL,
    labels          TEXT[] NOT NULL DEFAULT '{}',
    markdown_body   TEXT NOT NULL DEFAULT '',
    embedding       vector(768),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (provider, external_id)
);

CREATE INDEX IF NOT EXISTS idx_emails_provider_external_id ON emails (provider, external_id);
CREATE INDEX IF NOT EXISTS idx_emails_thread_id ON emails (thread_id);
CREATE INDEX IF NOT EXISTS idx_emails_sender ON emails (sender);
CREATE INDEX IF NOT EXISTS idx_emails_received_at ON emails (received_at DESC);
CREATE INDEX IF NOT EXISTS idx_emails_embedding ON emails USING hnsw (embedding vector_cosine_ops);

-- ─── topics ───
CREATE TABLE IF NOT EXISTS topics (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            TEXT NOT NULL,
    embedding       vector(768),
    snapshots       JSONB NOT NULL DEFAULT '[]',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_topics_embedding ON topics USING hnsw (embedding vector_cosine_ops);

-- ─── summaries ───
CREATE TABLE IF NOT EXISTS summaries (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    summary_type    TEXT NOT NULL CHECK (summary_type IN ('morning', 'evening')),
    date            DATE NOT NULL,
    markdown_body   TEXT NOT NULL DEFAULT '',
    embedding       vector(768),
    diff_hash       TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_summaries_type_date ON summaries (summary_type, date);
CREATE INDEX IF NOT EXISTS idx_summaries_embedding ON summaries USING hnsw (embedding vector_cosine_ops);

-- ─── task_lists ───
CREATE TABLE IF NOT EXISTS task_lists (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name                TEXT NOT NULL,
    google_tasklist_id  TEXT,
    position            INT NOT NULL DEFAULT 0,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ─── tasks ───
CREATE TABLE IF NOT EXISTS tasks (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title           TEXT NOT NULL,
    notes           TEXT NOT NULL DEFAULT '',
    status          TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'in_progress', 'done', 'cancelled')),
    priority        TEXT NOT NULL DEFAULT 'none' CHECK (priority IN ('none', 'low', 'medium', 'high')),
    due_date        TIMESTAMPTZ,
    completed_at    TIMESTAMPTZ,
    position        INT NOT NULL DEFAULT 0,
    list_id         UUID REFERENCES task_lists(id) ON DELETE SET NULL,
    parent_task_id  UUID REFERENCES tasks(id) ON DELETE CASCADE,
    source_email_id UUID REFERENCES emails(id) ON DELETE SET NULL,
    google_task_id  TEXT,
    last_synced_at  TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks (status);
CREATE INDEX IF NOT EXISTS idx_tasks_list_id ON tasks (list_id);
CREATE INDEX IF NOT EXISTS idx_tasks_parent_task_id ON tasks (parent_task_id);
CREATE INDEX IF NOT EXISTS idx_tasks_due_date ON tasks (due_date);
CREATE INDEX IF NOT EXISTS idx_tasks_source_email_id ON tasks (source_email_id);

-- ─── calendar_events ───
CREATE TABLE IF NOT EXISTS calendar_events (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    provider        TEXT NOT NULL CHECK (provider IN ('google', 'outlook')),
    external_id     TEXT NOT NULL,
    calendar_id     TEXT NOT NULL,
    title           TEXT NOT NULL,
    description     TEXT NOT NULL DEFAULT '',
    start_at        TIMESTAMPTZ NOT NULL,
    end_at          TIMESTAMPTZ NOT NULL,
    all_day         BOOLEAN NOT NULL DEFAULT false,
    location        TEXT NOT NULL DEFAULT '',
    recurrence      TEXT,
    status          TEXT NOT NULL DEFAULT 'confirmed' CHECK (status IN ('confirmed', 'tentative', 'cancelled')),
    organizer       TEXT,
    attendees       JSONB NOT NULL DEFAULT '[]',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (provider, external_id)
);

CREATE INDEX IF NOT EXISTS idx_calendar_events_time_range ON calendar_events (start_at, end_at);
CREATE INDEX IF NOT EXISTS idx_calendar_events_provider_calendar ON calendar_events (provider, calendar_id);

-- ─── sync_state ───
CREATE TABLE IF NOT EXISTS sync_state (
    provider        TEXT PRIMARY KEY CHECK (provider IN ('gmail', 'outlook')),
    history_id      TEXT,
    delta_link      TEXT,
    last_sync_at    TIMESTAMPTZ
);

-- ─── Junction Tables ───

-- emails <-> topics (many-to-many)
CREATE TABLE IF NOT EXISTS email_topics (
    email_id UUID NOT NULL REFERENCES emails(id) ON DELETE CASCADE,
    topic_id UUID NOT NULL REFERENCES topics(id) ON DELETE CASCADE,
    PRIMARY KEY (email_id, topic_id)
);

-- summaries <-> topics (many-to-many)
CREATE TABLE IF NOT EXISTS summary_topics (
    summary_id UUID NOT NULL REFERENCES summaries(id) ON DELETE CASCADE,
    topic_id   UUID NOT NULL REFERENCES topics(id) ON DELETE CASCADE,
    PRIMARY KEY (summary_id, topic_id)
);

-- tasks <-> topics (many-to-many)
CREATE TABLE IF NOT EXISTS task_topics (
    task_id  UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    topic_id UUID NOT NULL REFERENCES topics(id) ON DELETE CASCADE,
    PRIMARY KEY (task_id, topic_id)
);
