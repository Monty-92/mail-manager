-- mail-manager: Email Analysis Results
-- Stores LLM-generated analysis for each preprocessed email

-- ─── email_analyses ───
CREATE TABLE IF NOT EXISTS email_analyses (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email_id        UUID NOT NULL REFERENCES emails(id) ON DELETE CASCADE,
    category        TEXT NOT NULL DEFAULT 'other' CHECK (category IN (
                        'personal', 'work', 'transactional', 'newsletter',
                        'marketing', 'notification', 'spam', 'other'
                    )),
    urgency         TEXT NOT NULL DEFAULT 'normal' CHECK (urgency IN (
                        'critical', 'high', 'normal', 'low', 'none'
                    )),
    summary         TEXT NOT NULL DEFAULT '',
    action_items    JSONB NOT NULL DEFAULT '[]',
    key_topics      TEXT[] NOT NULL DEFAULT '{}',
    sentiment       TEXT NOT NULL DEFAULT 'neutral' CHECK (sentiment IN (
                        'positive', 'negative', 'neutral', 'mixed'
                    )),
    is_junk         BOOLEAN NOT NULL DEFAULT false,
    confidence      REAL NOT NULL DEFAULT 0.0,
    model_used      TEXT NOT NULL DEFAULT '',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (email_id)
);

CREATE INDEX IF NOT EXISTS idx_email_analyses_email_id ON email_analyses (email_id);
CREATE INDEX IF NOT EXISTS idx_email_analyses_category ON email_analyses (category);
CREATE INDEX IF NOT EXISTS idx_email_analyses_urgency ON email_analyses (urgency);
CREATE INDEX IF NOT EXISTS idx_email_analyses_is_junk ON email_analyses (is_junk);
