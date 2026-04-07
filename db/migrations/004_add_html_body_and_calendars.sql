-- mail-manager: Add html_body to emails + calendars table for multi-calendar support

-- ─── Add html_body to emails ───
-- Stores the original HTML content for rendering; markdown_body remains for embeddings/search
ALTER TABLE emails ADD COLUMN IF NOT EXISTS html_body TEXT NOT NULL DEFAULT '';

-- ─── Index emails.labels for label-based filtering ───
CREATE INDEX IF NOT EXISTS idx_emails_labels ON emails USING gin (labels);

-- ─── calendars table for multi-calendar support ───
CREATE TABLE IF NOT EXISTS calendars (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id      UUID NOT NULL REFERENCES connected_accounts(id) ON DELETE CASCADE,
    provider        TEXT NOT NULL CHECK (provider IN ('gmail', 'outlook')),
    external_id     TEXT NOT NULL,
    name            TEXT NOT NULL DEFAULT '',
    color           TEXT NOT NULL DEFAULT '#4285f4',
    is_primary      BOOLEAN NOT NULL DEFAULT false,
    enabled         BOOLEAN NOT NULL DEFAULT true,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (provider, external_id)
);

CREATE INDEX IF NOT EXISTS idx_calendars_account_id ON calendars (account_id);
