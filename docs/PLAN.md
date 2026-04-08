# Plan: mail-manager — Full Build Plan (v2 — Scope Expansion)

## TL;DR

mail-manager is a modular email-intelligence and personal productivity engine. It ingests emails from Gmail AND Microsoft 365 Outlook, analyzes them via local LLMs (Ollama), manages tasks/projects with subtasks and lists, provides a combined calendar view (Google + Outlook), and maintains living documents. 8 Python microservices + BFF + Vue 3 frontend, all running locally in Docker.

---

## Status

- **Phase A (Copilot config)**: ✅ DONE
- **Phase B (Repo scaffold)**: ✅ DONE — all 7 services + frontend scaffolded, tests passing
- **Scope expansion (B-patch)**: ✅ DONE — multi-provider schema, calendar-sync service, enhanced tasks, living docs updated
- **Phase C1 (Ingestion Service)**: ✅ DONE — full implementation with Gmail + Outlook providers, 35 tests passing
- **Phase C2 (Preprocessing)**: ✅ DONE — text cleaning, Ollama embeddings, Redis pipeline, 40 tests passing
- **Phase C3 (LLM Analysis)**: ✅ DONE — email categorization, urgency, action items, sentiment via Ollama, 39 tests passing
- **Phase C4 (Topic Tracking)**: ✅ DONE — 3-stage topic assignment, full CRUD, 25+ tests passing
- **Phase C5 (Summary Generation)**: ✅ DONE — daily/thread summaries, Ollama integration, 12+ tests passing
- **Phase C6 (Task Management)**: ✅ DONE — task CRUD with subtasks/lists, email extraction, 9+ tests passing
- **Phase C6.5 (Calendar Sync)**: ✅ DONE — Google + Outlook providers implemented, **44 tests passing**
- **Phase C7 (BFF Layer)**: ✅ DONE — auth flow, 61+ proxy endpoints, 33+ tests passing
- **Phase C8 (Frontend)**: ✅ DONE — all 9 views, 8 stores, full API wiring, HTML email rendering, label/category filtering
- **Phase D (Polish + Intelligence)**: ✅ DONE — RAG chat streaming, Google Tasks bidirectional sync, dashboard email stats (`email_stats` view, `pipeline_events` table), settings DB wiring (`user_config` table), pipeline audit log, migrations 004+005 applied

---

## Phase E and Beyond

See **[docs/COMPLETION_PLAN.md](COMPLETION_PLAN.md)** for the comprehensive remaining-work plan covering:

- Phase E1: Merge PR #20 to main
- Phase E2: Living documents update
- Phase E3: Immediate bug fixes (client.ts params, MSAL migration, escape sequence warning)
- Phase E4: Test coverage gap (lifespan mocking for out-of-Docker test runs)
- Phase E5: Security hardening (token encryption, in-memory store → DB)
- Phase E6: Frontend polish (stats store, settings persistence, chat refinements)
- Phase E7: Frontend testing (Vitest setup)
- Phase E8: E2E / pipeline smoke tests
- Phase E9: Production hardening (make migrate Windows fix, rate limiting, pagination)
- Phase F+: Future extensions (Notion, Slack, knowledge graph, calendar writes)

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

### C2. Preprocessing Service ✅ DONE
*Implementation complete with 40 passing tests.*
1. Subscribe to `mailmanager.email.new` Redis events (background listener)
2. Text cleaning and normalization (strip signatures, disclaimers, quoted replies)
3. Generate embeddings via Ollama (`nomic-embed-text`) using httpx
4. Store embeddings in pgvector column (`vector(768)`) via asyncpg
5. Publish `mailmanager.email.preprocessed` event to Redis
6. HTTP trigger endpoint: `POST /preprocess/{email_id}` for on-demand reprocessing
7. Tests: cleaner, embedder, pipeline, router, schemas, health, Docker build

### C3. LLM Analysis Service ✅ DONE
*Implementation complete with 39 passing tests.*
1. Subscribe to `mailmanager.email.preprocessed` Redis events (background listener)
2. Ollama LLM client — `/api/chat` with structured JSON prompts, `llama3.1:8b` model
3. Email categorization (8 categories), urgency detection (5 levels), sentiment analysis
4. Action item extraction with assignee and due hints
5. Key topic extraction (up to 5 per email)
6. Junk/spam classification with confidence scoring
7. Robust LLM response parsing with safe fallbacks for invalid/missing fields
8. asyncpg repository — store/retrieve analyses, find unanalyzed emails (LEFT JOIN)
9. Publish `mailmanager.email.analyzed` events to Redis
10. HTTP endpoints: `POST /analyze/{email_id}`, `POST /analyze/batch`, `GET /analyze/{email_id}`
11. Migration: `002_email_analyses.sql` — analysis results table with indexes
12. Tests: schemas (11), LLM client (3), analyzer (14), router (5), Docker (6)

### C4. Topic Tracking Service ✅ DONE
*Implementation complete with 25+ passing tests.*
1. 3-stage topic assignment: exact name match → pgvector embedding similarity → create new topic
2. Redis subscriber for `mailmanager.email.analyzed` events
3. Full CRUD endpoints: list, get, delete topics; assign topics to email; get email topics; get topic emails
4. Repository with `find_topic_by_name`, `find_similar_topics` (pgvector), `create_topic`, `link_email_topic`
5. Topic snapshot evolution tracking (JSONB)
6. Tests: matcher (11), router (14), schemas, Docker, health

### C5. Summary Generation Service ✅ DONE
*Implementation complete with 12+ passing tests.*
1. Daily summaries (morning 6 AM, evening 6 PM) via scheduled background task
2. Thread summarization endpoint
3. Ollama LLM integration with system prompts, daily/thread templates
4. Diff hash for dedup (skip regeneration if unchanged)
5. Repository: fetch emails for date range, store/retrieve summaries, link topics
6. Tests: generator (8), llm_client (4), router, schemas, Docker, health

### C6. Task Management Service ✅ DONE
*Implementation complete with 9+ passing tests.*
1. Task CRUD with subtasks (tree structure via `parent_task_id`)
2. Task list CRUD (create/rename/delete/reorder lists)
3. Priority and due date management
4. Task extraction from LLM analysis action items with urgency→priority mapping
5. Idempotency check (skip if tasks already extracted for email)
6. Redis subscriber for `mailmanager.email.analyzed` events
7. Tests: extractor (9), router, schemas, Docker, health

### C6.5. Calendar Sync Service ⚠️ PARTIAL
*Implementation complete, tests needed.*
1. Google Calendar API v3 client — OAuth token refresh, fetch/create/update events with pagination
2. Microsoft Graph Calendar API — MSAL auth, fetch/create/update with OData pagination
3. Unified calendar event model → upsert into `calendar_events` table (ON CONFLICT UPDATE)
4. Router: list events (filtered), list sources, sync calendar, delete event
5. Repository: get_events, upsert_calendar_event, get_calendar_accounts, delete_event
6. **TODO: Add router tests, provider tests, integration tests**

### C7. BFF Layer ✅ DONE
*Implementation complete with 70+ passing tests.*
1. Authentication: setup, login (password + TOTP 2FA), JWT sessions (24h), middleware
2. 61+ proxy endpoints to all 7 downstream services
3. httpx AsyncClient with 30s timeout (600s for summary generation)
4. Auth middleware for protected routes, public paths for setup/login
5. Tests: ingestion (6), preprocessing (4), analysis (5), topics (11), summaries (9), tasks (28), Docker (10), health (2)

### C8. Frontend ✅ DONE
*All views and stores implemented.*
1. 9 views: Login, Setup, AuthCallback, Dashboard, EmailBrowser, TaskManager, TopicExplorer, Calendar, Settings
2. 7/8 Pinia stores complete (chat store is placeholder pending backend)
3. 11 API client modules (~40+ functions), all wired to `/api/v1/`
4. 11 reusable UI components with light/dark theming
5. Auth guards, OAuth callback handling, TOTP 2FA flow
6. Comprehensive TypeScript types (~200 lines of domain models)

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
