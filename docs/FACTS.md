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

## Database Tables
- emails (provider-agnostic: provider + external_id composite unique)
- sync_state (provider PK, history_id for Gmail, delta_link for Outlook)
- email_analyses (category, urgency, summary, action_items JSONB, key_topics, sentiment, is_junk, confidence)
- topics, summaries
- task_lists (containers for tasks, synced with Google Task lists)
- tasks (enhanced: title, notes, priority, due_date, completed_at, position, list_id, parent_task_id)
- calendar_events (provider + external_id, Google + Outlook)
- app_user (single-user: username, password_hash bcrypt, totp_secret, setup_complete)
- connected_accounts (provider, email, access_token, refresh_token, token_expiry, scopes)
- Junction: email_topics, summary_topics, task_topics

## Build Phase Status
- Phase A (Copilot config): DONE
- Phase B (Repo scaffold): DONE
- Phase B-PATCH (Scope expansion): DONE
- Phase C1 (Ingestion Service): DONE — 35 tests passing
- Phase C2 (Preprocessing): DONE — 40 tests passing
- Phase C3 (LLM Analysis): DONE — 39 tests passing
- Phase C4 (Topic Tracking): DONE — 25+ tests passing
- Phase C5 (Summary Generation): DONE — 12+ tests passing
- Phase C6 (Task Management): DONE — 9+ tests passing
- Phase C6.5 (Calendar Sync): PARTIAL — logic implemented, tests needed (only health test)
- Phase C7 (BFF Layer): DONE — 70+ tests passing
- Phase C8 (Frontend): DONE — all views, stores, API wiring complete
- Phase D (Polish): NOT STARTED

## Testing
- All services: `cd services/<name> && uv run pytest`
- Ingestion: 35 tests (converter: 12, providers: 10, router: 5, schemas: 7, health: 1)
- Preprocessing: 40 tests (cleaner, embedder, pipeline, router, schemas, health, Docker)
- LLM Analysis: 39 tests (schemas: 11, LLM client: 3, analyzer: 14, router: 5, Docker: 6)
- Topic Tracking: 25+ tests (matcher: 11, router: 14)
- Summary Generation: 12+ tests (generator: 8, llm_client: 4)
- Task Management: 9+ tests (extractor: 9)
- Calendar Sync: 1 test (health only — **tests needed**)
- BFF: 70+ tests (ingestion: 6, preprocessing: 4, analysis: 5, topics: 11, summaries: 9, tasks: 28, Docker: 10, health: 2)
- Total: 230+ tests passing across all services
