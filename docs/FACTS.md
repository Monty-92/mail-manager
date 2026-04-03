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
- topics, summaries
- task_lists (containers for tasks, synced with Google Task lists)
- tasks (enhanced: title, notes, priority, due_date, completed_at, position, list_id, parent_task_id)
- calendar_events (provider + external_id, Google + Outlook)
- Junction: email_topics, summary_topics, task_topics

## Build Phase Status
- Phase A (Copilot config): DONE
- Phase B (Repo scaffold): DONE
- Phase B-PATCH (Scope expansion): DONE
- Phase C1 (Ingestion Service): DONE — 35 tests passing
- Phase C2 (Preprocessing): NOT STARTED — next priority
- Phase C3–C8: NOT STARTED
- Phase D (Polish): NOT STARTED

## Testing
- All services: `cd services/<name> && uv run pytest`
- Ingestion: 35 tests (converter: 12, providers: 10, router: 5, schemas: 7, health: 1)
- Other 7 services: 1 health test each (7 tests)
- Total: 42 tests passing across all services
