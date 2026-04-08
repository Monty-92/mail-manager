# mail-manager — Repository Facts

## Architecture
- 8 Python microservices + 1 Vue 3 frontend + BFF layer
- Services: ingestion, preprocessing, llm-analysis, topic-tracking, summary-generation, task-management, calendar-sync, bff
- All services use `src/<package>/` layout with hatchling build backend
- FastAPI uses `lifespan` context manager (NOT deprecated `@app.on_event`)
- Each service has health check at `GET /health` returning `{"status": "ok"}`

## Key Decisions
- Embedding model: nomic-embed-text → vector(768)
- LLM: Ollama container, default model llama3.1:8b, configurable from UI
- Python 3.12, uv managed, hatchling build backend
- Frontend: Vue 3 + Tailwind + TypeScript, npm
- Service comms: HTTP + Redis pub/sub hybrid
- Email providers: Gmail (push + polling) + Microsoft 365 Outlook (Graph API, personal account)
- Ingestion pattern: single service with provider adapters (not separate services)
- Task management: enhanced with subtasks (parent_task_id), task_lists, priorities, due dates
- Calendar: read-only aggregation of Google Calendar + Outlook Calendar
- Auth: Google OAuth + Microsoft OAuth (personal, tenant=common)

## Ports
- BFF: 8000
- Ingestion: 8001
- Preprocessing: 8002
- LLM Analysis: 8003
- Topic Tracking: 8004
- Summary Generation: 8005
- Task Management: 8006
- Calendar Sync: 8007
- Frontend: 3000
- Postgres: 5432
- Redis: 6379
- Ollama: 11434

## Database Tables (migrations 001–005 applied)
- emails (provider-agnostic: provider + external_id composite unique; includes html_body TEXT column added in 004)
- sync_state (provider PK, history_id for Gmail, delta_link for Outlook)
- email_analyses (category, urgency, summary, action_items JSONB, key_topics, sentiment, is_junk, confidence)
- topics, summaries
- task_lists (containers for tasks, synced with Google Task lists)
- tasks (enhanced: title, notes, priority, due_date, completed_at, position, list_id, parent_task_id, calendar_account_id FK)
- calendar_events (provider + external_id, Google + Outlook)
- calendars (provider, external_id, account_id FK, name, description, color, is_primary, is_selected, sync token)
- app_user (single-user: username, password_hash bcrypt, totp_secret, setup_complete)
- connected_accounts (provider, email, access_token, refresh_token, token_expiry, scopes)
- user_config (key-value config table: llm_model, embed_model, auto_sync, auto_analyze, default_calendar)
- pipeline_events (stage, email_id FK nullable, details JSONB, occurred_at; indexes on stage, email_id, occurred_at)
- Junction: email_topics, summary_topics, task_topics
- View: email_stats (total_emails, emails_today, unread_emails, preprocessed_emails, analyzed_emails)

## Build Phase Status
- Phase A (Copilot config): DONE
- Phase B (Repo scaffold): DONE
- Phase B-PATCH (Scope expansion): DONE
- Phase C1 (Ingestion Service): DONE — Gmail + Outlook providers, 52 tests passing
- Phase C2 (Preprocessing): DONE — 17 tests passing
- Phase C3 (LLM Analysis): DONE — 17 tests passing (+ Docker test)
- Phase C4 (Topic Tracking): DONE — matcher + router tests (Docker test only outside Docker)
- Phase C5 (Summary Generation): DONE — Docker test + unit tests (Docker test only outside Docker)
- Phase C6 (Task Management): DONE — extractor tests (Docker test only outside Docker)
- Phase C6.5 (Calendar Sync): DONE — 44 tests passing (Google + Outlook providers, full router coverage)
- Phase C7 (BFF Layer): DONE — 33 tests passing (auth, all proxy endpoints)
- Phase C8 (Frontend): DONE — all views, stores, API wiring, HTML rendering, label/category filters
- Phase D (Intelligence + Polish): DONE — RAG chat, Google Tasks bidirectional sync, dashboard stats, settings DB, pipeline audit log

## Testing (actual baseline — post-Phase D stabilisation)
- BFF: 33 passed — `cd services/bff && uv run pytest`
- Ingestion: 52 passed, 2 known failures (test_sync/fetch_without_auth hit DB before auth check)
- Preprocessing: 17 passed
- LLM Analysis: 17 passed
- Calendar Sync: 44 passed
- Topic Tracking / Summary Generation / Task Management: 1 passed each outside Docker (test_docker.py only; other tests hang on lifespan DB connection — needs lifespan mocking)
- Total baseline: 166 passed, 2 known pre-existing failures

## Known Limitations / Issues
- `make migrate` fails on Windows (Git's psql has incompatible path handling); workaround: `docker compose cp` + `docker compose exec postgres psql -f`
- Topic-tracking/summary-gen/task-mgmt conftest.py has no lifespan mocking → tests hang outside Docker
- Ingestion `_token_store` is in-memory dict (lost on restart); needs DB-backed storage
- OAuth tokens stored in plaintext in `connected_accounts` table; should be encrypted
- MSAL `get_authorization_request_url()` is deprecated; should migrate to `initiate_auth_code_flow()`
- `client.ts post()` has no query-params support; `fetchProvider`/`syncProvider` in `ingestion.ts` don't pass params
- Ingestion `repository.py` ~L191: SyntaxWarning for invalid escape sequence `\_` in SQL string
