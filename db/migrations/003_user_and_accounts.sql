-- mail-manager: User authentication and connected provider accounts
-- Adds app_user for single-user login with TOTP 2FA
-- Adds connected_accounts for OAuth token persistence (multi-account per provider)

-- ─── app_user ───
CREATE TABLE IF NOT EXISTS app_user (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username            TEXT NOT NULL UNIQUE,
    password_hash       TEXT NOT NULL,
    totp_secret         TEXT,
    is_setup_complete   BOOLEAN NOT NULL DEFAULT false,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ─── connected_accounts ───
CREATE TABLE IF NOT EXISTS connected_accounts (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    provider        TEXT NOT NULL CHECK (provider IN ('gmail', 'outlook')),
    email           TEXT NOT NULL,
    display_name    TEXT NOT NULL DEFAULT '',
    access_token    TEXT NOT NULL,
    refresh_token   TEXT,
    token_expiry    TIMESTAMPTZ,
    scopes          TEXT[] NOT NULL DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (provider, email)
);

CREATE INDEX IF NOT EXISTS idx_connected_accounts_provider ON connected_accounts (provider);
