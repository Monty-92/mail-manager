# Plan: mail-manager — Full Build Plan (v2 — Scope Expansion)

## TL;DR

mail-manager is a modular email-intelligence and personal productivity engine. It ingests emails from Gmail AND Microsoft 365 Outlook, analyzes them via local LLMs (Ollama), manages tasks/projects with subtasks and lists, provides a combined calendar view (Google + Outlook), and maintains living documents. 8 Python microservices + BFF + Vue 3 frontend, all running locally in Docker.

---

## Status

- **Phase A (Copilot config)**: ✅ DONE
- **Phase B (Repo scaffold)**: ✅ DONE — all 7 services + frontend scaffolded, tests passing
- **Scope expansion (B-patch)**: ✅ DONE — multi-provider schema, calendar-sync service, enhanced tasks, living docs updated
- **Phase C1 (Ingestion Service)**: ✅ DONE — full implementation with Gmail + Outlook providers, 35 tests passing
- **Phase C2 (Preprocessing)**: NOT STARTED
- **Phase C3–C8**: NOT STARTED

---

## Decisions Captured (original + scope expansion)

- **Build order**: Ingestion → Preprocessing → LLM Analysis → Topic Tracking → Summary Gen → Task Mgmt → Calendar Sync → BFF → Frontend
- **LLM runtime**: Ollama Docker container, default `llama3.1:8b`, configurable from UI
- **Embedding model**: `nomic-embed-text` (768d) → `vector(768)`
- **Python**: 3.12, `uv` managed, hatchling build backend, src layout
- **Frontend**: Vue 3 + Tailwind + TypeScript strict, `npm`
- **Service comms**: Hybrid HTTP + Redis pub/sub
- **Email providers**: Gmail (push + polling) AND Microsoft 365 Outlook (Microsoft Graph API, personal account)
- **Ingestion pattern**: Single ingestion service with provider adapters (not separate services)
- **Task management**: Enhanced for project management — subtasks, task lists, due dates, priorities, notes
- **Task backend**: Google Tasks as primary external sync target
- **Calendar**: New calendar-sync service (port 8007), read-only Google + Outlook calendar aggregation
- **Auth**: Google OAuth + Microsoft OAuth (personal account, common tenant)
- **Living doc maintenance**: On-demand Copilot skill
- **Project name**: Keep "mail-manager"

---

## Phase C: Core Services Build (Updated)

### C1. Ingestion Service ✅ DONE
*Implementation complete with 35 passing tests.*
1. Provider adapter pattern: `BaseEmailProvider` ABC with `GmailProvider` and `OutlookProvider` implementations
2. Gmail: OAuth 2.0 flow, token storage/refresh, Gmail API client, historical batch + incremental sync (history API)
3. Outlook: Microsoft Graph API via MSAL, token storage/refresh, mail/messages endpoint, delta queries for incremental sync
4. Email → Markdown converter (beautifulsoup4 + markdownify, shared across providers)
5. Postgres writer — asyncpg pool, store with `provider` + `external_id` dedup (ON CONFLICT DO NOTHING)
6. Publish `mailmanager.email.new` events to Redis (redis.asyncio)
7. sync_state table for tracking history_id (Gmail) and delta_link (Outlook)
8. FastAPI router: auth URL generation, OAuth callback, incremental sync, full fetch
9. Tests: converter (12), providers (10), router (5), schemas (7), health (1)

### C2. Preprocessing Service
*Next priority. Depends on: C1 complete.*
1. Subscribe to `mailmanager.email.new` Redis events
2. Text cleaning and normalization
3. Generate embeddings via Ollama (`nomic-embed-text`)
4. Store embeddings in pgvector column (`vector(768)`)
5. Update relational links

### C3. LLM Analysis Service
1. Consume preprocessed emails
2. Categorization, urgency detection, action item extraction
3. Store analysis results
4. Trigger downstream events

### C4. Topic Tracking Service
1. Topic detection and clustering
2. Thread/conversation tracking
3. Topic evolution over time

### C5. Summary Generation Service
1. Email thread summarization
2. Daily/weekly digest generation
3. Topic-based summaries

### C6. Task Management Service
*Enhanced for project management*
1. Task CRUD with subtasks (tree structure via `parent_task_id`)
2. Task list CRUD (create/rename/delete/reorder lists)
3. Priority and due date management
4. Google Tasks API bidirectional sync (lists ↔ task_lists, tasks ↔ tasks)
5. Task extraction from LLM analysis results
6. Position/ordering logic within lists
7. Conflict resolution + sync metadata

### C6.5. Calendar Sync Service
*Parallel with: C4, C5, C6*
1. Google Calendar API client — OAuth, read-only fetch of events
2. Microsoft Graph Calendar API — MSAL auth, read-only fetch
3. Unified calendar event model → store in `calendar_events` table
4. Incremental sync (delta tokens for both providers)
5. BFF exposes aggregated calendar endpoint

### C7. BFF Layer
- Add `/api/v1/calendar/events` endpoint aggregating calendar-sync service
- Add `/api/v1/tasks/lists` endpoints for task list management
- Add `/api/v1/tasks/{id}/subtasks` endpoints

### C8. Frontend
- Calendar view: month/week/day views, combined Google + Outlook events, color-coded by provider
- Task manager: list-based view, subtask tree, drag-to-reorder, due dates, priority badges
- Settings: add Microsoft account connection flow

---

## C1 Implementation Details (for reference)

### Files Created
- `services/ingestion/src/ingestion/schemas.py` — Pydantic models (EmailProvider, RawEmail, StoredEmail, IngestResult, OAuthTokens, SyncState)
- `services/ingestion/src/ingestion/repository.py` — asyncpg pool, upsert_email, get_sync_state, save_sync_state
- `services/ingestion/src/ingestion/converter.py` — html_to_markdown (BS4 + markdownify), email_body_to_markdown
- `services/ingestion/src/ingestion/providers/__init__.py` — BaseEmailProvider ABC
- `services/ingestion/src/ingestion/providers/gmail.py` — GmailProvider (OAuth, fetch, history API incremental sync)
- `services/ingestion/src/ingestion/providers/outlook.py` — OutlookProvider (MSAL, Graph API, delta queries)
- `services/ingestion/src/ingestion/publisher.py` — Redis pub/sub publisher
- `services/ingestion/src/ingestion/router.py` — FastAPI router (auth URL, callback, sync, fetch endpoints)

### Files Modified
- `services/ingestion/src/ingestion/main.py` — Router include, DB/Redis cleanup in lifespan
- `db/migrations/001_initial_schema.sql` — Added sync_state table

### Known Simplifications
- `_token_store` in router.py is in-memory dict — production would use encrypted DB storage
- MSAL deprecation warning on `get_authorization_request_url()` — should migrate to `initiate_auth_code_flow()`

---

## Scope Boundaries

**Included**: Gmail + Outlook email ingestion, local LLM analysis, living docs, web UI, Google Tasks sync with project management features (subtasks, lists, due dates), combined calendar view (read-only), Copilot config
**Excluded (future)**: Notion integration, Slack/Teams, knowledge graph, multi-agent orchestration, Chrome extension, CI/CD pipeline, calendar write operations (create/edit events)
