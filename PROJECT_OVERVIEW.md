# mail-manager — Project Overview

## 1. Vision

**mail-manager** is a modular, extensible email-intelligence and personal productivity engine. It ingests emails from **Gmail** and **Microsoft 365 Outlook**, analyzes them using locally hosted LLMs, and maintains *living documents* that always reflect the current state of tasks, topics, and daily summaries.

Beyond email intelligence, mail-manager provides **project management** features (tasks with subtasks, lists, priorities, and due dates) and a **combined calendar view** aggregating Google Calendar and Outlook Calendar events.

It is designed as a reusable intelligence layer that can be embedded into a broader personal knowledge management (PKM) system and expanded to additional data sources such as Notion and Slack.

> **Core mission:** transform raw communication streams into structured, queryable, and continuously updated knowledge — entirely on local infrastructure, with no paid cloud services.

---

## 2. Core Objectives

| # | Objective |
|---|-----------|
| 1 | Ingest both historical and new emails from Gmail and Microsoft 365 Outlook |
| 2 | Convert emails to Markdown for readability and LLM-friendliness |
| 3 | Store all data (emails, summaries, tasks, topics, calendar events) in PostgreSQL |
| 4 | Use `pgvector` for embeddings and semantic search |
| 5 | Group emails by thread and semantic topic |
| 6 | Generate daily summaries (morning + evening) |
| 7 | Maintain evolving topic snapshots |
| 8 | Detect junk mail while surfacing potentially valuable promotions |
| 9 | Extract action items and sync them bidirectionally with Google Tasks |
| 10 | Provide project management with task lists, subtasks, priorities, and due dates |
| 11 | Display a combined calendar view (Google Calendar + Outlook Calendar, read-only) |
| 12 | Produce and update Markdown-based living documents |
| 13 | Provide a modern web UI for browsing insights and interacting with the system |

---

## 3. Technical Constraints

The system relies **exclusively** on free and open-source technologies. No paid cloud services or proprietary LLM APIs are permitted.

| Category | Technology |
|----------|-----------|
| Containerization | [Docker](https://www.docker.com/) |
| Orchestration | [Docker Compose](https://docs.docker.com/compose/) |
| Python environments | [uv](https://github.com/astral-sh/uv) by Astral |
| Database | [PostgreSQL](https://www.postgresql.org/) + [pgvector](https://github.com/pgvector/pgvector) |
| Local LLM inference | [Ollama](https://ollama.com/) (default model: llama3.1:8b, embeddings: nomic-embed-text) |
| Backend framework | [FastAPI](https://fastapi.tiangolo.com/) (or equivalent free framework) |
| Frontend | [Vue 3](https://vuejs.org/) + [Tailwind CSS](https://tailwindcss.com/) + TypeScript |
| Email integration | Gmail API (free tier), Microsoft Graph API (free tier) |
| Task integration | Google Tasks API (free tier) |
| Calendar integration | Google Calendar API + Microsoft Graph Calendar API (read-only) |

**Guiding principles:** reproducibility, local execution, and modularity. Every developer must be able to run the full stack with `docker compose up`.

---

## 4. Architecture Overview

mail-manager follows a **microservice architecture** with a dedicated **Backend-for-Frontend (BFF)** layer that shields the UI from internal service complexity.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           Frontend (Vue 3)                              │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │ HTTP / WebSocket
┌────────────────────────────────────▼────────────────────────────────────┐
│                          BFF Layer (FastAPI)                             │
└──┬──────────┬──────────┬──────────┬──────────┬──────────┬──────────┬───┘
   │          │          │          │          │          │          │
   ▼          ▼          ▼          ▼          ▼          ▼          ▼
Ingest  Preprocess  LLM Analysis  Topic   Summary   Task Mgmt  Calendar
Service  Service     Service    Tracking  Service   Service     Sync
   │          │          │          │          │          │          │
   └──────────┴──────────┴──────────┴──────────┴──────────┴──────────┘
                                     │
                          ┌──────────▼──────────┐
                          │  PostgreSQL + pgvector │
                          └─────────────────────┘
```

### 4.1 Ingestion Service

- Multi-provider email ingestion via a provider-adapter pattern
- **Gmail**: connects via Gmail API using OAuth 2.0; fetches historical and new/streaming emails
- **Outlook**: connects via Microsoft Graph API using MSAL; fetches messages with delta queries
- Converts raw email payloads to clean Markdown (shared converter)
- Stores email content, metadata, and embeddings in Postgres
- Deduplicates by `(provider, external_id)` composite key

### 4.2 Preprocessing & Normalization Service

- Cleans and normalizes text (strip HTML, fix encoding, etc.)
- Extracts structured metadata (sender, recipients, thread ID, labels, timestamps)
- Generates vector embeddings via a local embedding model
- Updates relational links between emails, threads, and topics

### 4.3 LLM Analysis Service

- Runs locally in Docker using Llama-compatible models (via Llama.cpp or Ollama)
- Responsibilities:
  - **Summarization** — produce concise email summaries
  - **Topic extraction** — identify and cluster semantic topics
  - **Action-item detection** — surface tasks and follow-ups
  - **Junk / deal classification** — separate noise from value
  - **RAG-powered chat** — answer natural-language questions about emails, topics, and summaries by retrieving relevant context via pgvector similarity search and streaming responses via SSE

### 4.4 Topic Tracking Service

- Maintains topic entities as first-class database records
- Tracks topic evolution over time (version history / snapshots)
- Links topics to emails, summaries, and tasks
- Supports semantic similarity queries via pgvector

### 4.5 Summary Generation Service

- Produces daily **morning** and **evening** summaries
- Stores summaries as Markdown in Postgres
- Generates embeddings and diff hashes for each summary version
- Supports re-generation when the underlying email set changes

### 4.6 Task Management Service

- Enhanced project management: task lists, subtasks, priorities, due dates
- Stores tasks organized in lists with ordering (position), subtask trees via `parent_task_id`
- Extracts tasks and action items from emails
- Syncs **bidirectionally** with Google Tasks API (lists ↔ task_lists, tasks ↔ tasks)
- Maintains sync metadata (external task ID, last-sync timestamp, conflict state)
- Google Tasks client built with `google-api-python-client`; tokens sourced from `connected_accounts`

### 4.7 Calendar Sync Service

- Aggregates calendar events from Google Calendar and Outlook Calendar (read-only)
- **Google Calendar**: connects via Google Calendar API using OAuth 2.0
- **Outlook Calendar**: connects via Microsoft Graph Calendar API using MSAL
- Stores unified calendar events in Postgres with incremental sync (delta tokens)
- Exposes events to the BFF for the combined calendar UI view

### 4.8 BFF Layer

- Provides a clean, versioned REST API for the UI at `/api/v1/`
- Aggregates and shapes data from multiple internal services
- Handles user authentication and permission checks
- Endpoints include: auth (setup/login/TOTP), email browser, ingestion triggers, preprocessing, LLM analysis, topics, summaries, tasks, calendar, accounts, chat (SSE streaming), stats (dashboard + pipeline), settings (user_config CRUD)

### 4.9 Frontend (Vue 3 + Tailwind CSS + TypeScript)

- Renders living documents (tasks, topics, summaries) in Markdown
- Displays dashboards with filtering and search
- Provides email-insight views and topic drill-downs
- Task manager with list-based views, subtask trees, priorities, and due dates
- Combined calendar view (Google + Outlook events, color-coded by provider)
- Settings page for Ollama model selection and provider connections

### 4.10 Orchestration

- All services are defined in a single `docker-compose.yml` at the repository root
- Python services use `uv` for environment and dependency management
- Postgres + pgvector serves as the single source of truth
- Health-check and dependency ordering enforced via Docker Compose `depends_on`

---

## 5. Data Model

All data is stored in PostgreSQL to ensure consistent querying, semantic search, and future extensibility. `pgvector` columns hold vector embeddings for similarity search.

### 5.1 `emails`

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID PK | Internal identifier |
| `provider` | TEXT | Email provider (`gmail` or `outlook`) |
| `external_id` | TEXT | Provider-specific message ID (dedup key with provider) |
| `thread_id` | TEXT | Thread/conversation ID (nullable — Outlook may not have one) |
| `sender` | TEXT | Sender email address |
| `recipients` | TEXT[] | To / CC / BCC addresses |
| `subject` | TEXT | Email subject line |
| `received_at` | TIMESTAMPTZ | Received timestamp |
| `labels` | TEXT[] | Provider labels/categories |
| `markdown_body` | TEXT | Full email body as Markdown |
| `html_body` | TEXT | Raw HTML body (preserved for rendering) |
| `embedding` | vector(768) | Semantic embedding (pgvector, nomic-embed-text) |
| `created_at` | TIMESTAMPTZ | Row creation timestamp |

Unique constraint: `(provider, external_id)`. Relationships: many-to-many with `topics` and `tasks`.

### 5.2 `topics`

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID PK | Internal identifier |
| `name` | TEXT | Human-readable topic name |
| `embedding` | vector(768) | Semantic embedding |
| `snapshots` | JSONB | Ordered array of evolution snapshots |
| `created_at` | TIMESTAMPTZ | Row creation timestamp |
| `updated_at` | TIMESTAMPTZ | Last snapshot update |

Relationships: many-to-many with `emails`, `summaries`, and `tasks`.

### 5.3 `summaries`

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID PK | Internal identifier |
| `summary_type` | TEXT | `morning` or `evening` |
| `date` | DATE | Summary date |
| `markdown_body` | TEXT | Summary content as Markdown |
| `embedding` | vector(768) | Semantic embedding |
| `diff_hash` | TEXT | SHA hash for change detection |
| `created_at` | TIMESTAMPTZ | Row creation timestamp |

Relationships: many-to-many with `topics`.

### 5.4 `tasks`

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID PK | Internal identifier |
| `title` | TEXT | Task title |
| `notes` | TEXT | Extended description / body |
| `status` | TEXT | `pending`, `in_progress`, `done`, `cancelled` |
| `priority` | TEXT | `none`, `low`, `medium`, `high` |
| `due_date` | TIMESTAMPTZ | Optional due date |
| `completed_at` | TIMESTAMPTZ | When the task was completed |
| `position` | INT | Ordering position within a list |
| `list_id` | UUID FK → `task_lists` | Task list this task belongs to |
| `parent_task_id` | UUID FK → `tasks` | Parent task (for subtasks) |
| `source_email_id` | UUID FK → `emails` | Email the task was extracted from |
| `google_task_id` | TEXT | External Google Tasks ID |
| `last_synced_at` | TIMESTAMPTZ | Last bidirectional sync timestamp |
| `created_at` | TIMESTAMPTZ | Row creation timestamp |
| `updated_at` | TIMESTAMPTZ | Last modification timestamp |

Relationships: many-to-many with `topics`. Self-referencing via `parent_task_id` for subtasks.

### 5.5 `task_lists`

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID PK | Internal identifier |
| `name` | TEXT | List name |
| `google_tasklist_id` | TEXT | External Google Tasks list ID |
| `position` | INT | Ordering position |
| `created_at` | TIMESTAMPTZ | Row creation timestamp |
| `updated_at` | TIMESTAMPTZ | Last modification timestamp |

### 5.6 `calendar_events`

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID PK | Internal identifier |
| `provider` | TEXT | Calendar provider (`google` or `outlook`) |
| `external_id` | TEXT | Provider-specific event ID |
| `calendar_id` | TEXT | Provider calendar ID |
| `title` | TEXT | Event title |
| `description` | TEXT | Event description |
| `start_at` | TIMESTAMPTZ | Event start time |
| `end_at` | TIMESTAMPTZ | Event end time |
| `all_day` | BOOLEAN | Whether the event spans full day(s) |
| `location` | TEXT | Event location |
| `recurrence` | TEXT | RRULE recurrence string |
| `status` | TEXT | `confirmed`, `tentative`, `cancelled` |
| `organizer` | TEXT | Organizer email |
| `attendees` | JSONB | Array of attendee objects |
| `created_at` | TIMESTAMPTZ | Row creation timestamp |
| `updated_at` | TIMESTAMPTZ | Last modification timestamp |

Unique constraint: `(provider, external_id)`.

### 5.7 `email_analyses`

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID PK | Internal identifier |
| `email_id` | UUID FK → `emails` | Analyzed email |
| `category` | TEXT | `personal`, `work`, `transactional`, `newsletter`, `marketing`, `notification`, `spam`, `other` |
| `urgency` | TEXT | `critical`, `high`, `normal`, `low`, `none` |
| `summary` | TEXT | LLM-generated single-line summary |
| `action_items` | JSONB | Structured action items with assignee/due hints |
| `key_topics` | TEXT[] | Up to 5 topic strings |
| `sentiment` | TEXT | `positive`, `negative`, `neutral`, `mixed` |
| `is_junk` | BOOLEAN | Junk/spam classification |
| `confidence` | FLOAT | Classification confidence score |
| `created_at` | TIMESTAMPTZ | Row creation timestamp |

### 5.8 `app_user`

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID PK | Internal identifier |
| `username` | TEXT UNIQUE | Login username |
| `password_hash` | TEXT | bcrypt-hashed password |
| `totp_secret` | TEXT | TOTP 2FA secret key |
| `setup_complete` | BOOLEAN | Whether initial setup is done |
| `created_at` | TIMESTAMPTZ | Row creation timestamp |

### 5.9 `connected_accounts`

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID PK | Internal identifier |
| `provider` | TEXT | `gmail` or `outlook` |
| `email` | TEXT | Provider account email |
| `display_name` | TEXT | User display name |
| `access_token` | TEXT | OAuth access token |
| `refresh_token` | TEXT | OAuth refresh token |
| `token_expiry` | TIMESTAMPTZ | Token expiration time |
| `scopes` | TEXT[] | Granted OAuth scopes |
| `created_at` | TIMESTAMPTZ | Row creation timestamp |

Unique constraint: `(provider, email)`.

### 5.10 `calendars`

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID PK | Internal identifier |
| `provider` | TEXT | `gmail` or `outlook` |
| `external_id` | TEXT | Provider calendar ID |
| `account_id` | UUID FK → `connected_accounts` | Owning account |
| `name` | TEXT | Calendar display name |
| `description` | TEXT | Calendar description |
| `color` | TEXT | Display color |
| `is_primary` | BOOLEAN | Primary calendar flag |
| `is_selected` | BOOLEAN | Whether selected for sync |
| `sync_token` | TEXT | Incremental sync token |
| `created_at` | TIMESTAMPTZ | Row creation timestamp |

Unique constraint: `(provider, external_id)`.

### 5.11 `user_config`

| Column | Type | Description |
|--------|------|-------------|
| `key` | TEXT PK | Config key |
| `value` | TEXT | Config value |
| `updated_at` | TIMESTAMPTZ | Last update timestamp |

Pre-seeded keys: `llm_model` (`llama3.1:8b`), `embed_model` (`nomic-embed-text`), `auto_sync` (`true`), `auto_analyze` (`true`), `default_calendar` (`google`).

### 5.12 `pipeline_events`

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID PK | Internal identifier |
| `stage` | TEXT | Pipeline stage name (e.g. `ingested`, `preprocessed`, `analyzed`) |
| `email_id` | UUID FK → `emails` nullable | Associated email (nullable for non-email events) |
| `details` | JSONB | Stage-specific details |
| `occurred_at` | TIMESTAMPTZ | When the event occurred |

Indexes on `stage`, `email_id`, `occurred_at DESC`.

### 5.13 `email_stats` (view)

A materialized-style view computing:
- `total_emails` — total row count
- `emails_today` — rows with `received_at::date = CURRENT_DATE`
- `unread_emails` — rows where `'UNREAD'` is in labels
- `preprocessed_emails` — emails with non-null `embedding`
- `analyzed_emails` — emails with a corresponding `email_analyses` row

---

## 6. Living Documents

mail-manager maintains a set of **living documents** — Markdown files that are continuously regenerated as new data arrives.

| Document | Description |
|----------|-------------|
| **Task state document** | A single Markdown file representing all open tasks; regenerated whenever task state changes |
| **Daily summaries** | Morning and evening Markdown summaries stored in Postgres and renderable in the UI |
| **Topic snapshots** | Per-topic Markdown snapshots that evolve as new emails are linked |

### Design requirements for living documents

- **Human-readable** — formatted Markdown that makes sense when read directly
- **LLM-friendly** — structured enough to be fed back to an LLM as context
- **Diff-friendly** — deterministic output so version diffs are meaningful; diff hashes stored alongside each version
- **Renderable in the UI** — the frontend renders Markdown natively; no HTML pre-processing required

---

## 7. Extensibility

The architecture is intentionally service-oriented so that new capabilities can be added as independent services without modifying existing ones.

Planned future extensions include:

- **Notion integration** — push living documents and task states to Notion pages
- **Additional communication channels** — Slack, Microsoft Teams, SMS
- **Knowledge-graph expansion** — build an entity graph (people, organizations, projects) across all data sources
- **Multi-agent orchestration** — coordinate specialized LLM agents for research, drafting, and scheduling
- **Calendar write operations** — create and edit events from within mail-manager

New services will follow the same patterns: a dedicated Postgres schema, a `uv`-managed Python environment, a Dockerfile, and a service definition in `docker-compose.yml`.

---

## 8. Repository Structure (target)

```
mail-manager/
├── PROJECT_OVERVIEW.md          # This file
├── README.md                    # Quick-start guide
├── docker-compose.yml           # Full stack definition
├── services/
│   ├── ingestion/               # 4.1 Ingestion Service (Gmail + Outlook)
│   ├── preprocessing/           # 4.2 Preprocessing & Normalization Service
│   ├── llm-analysis/            # 4.3 LLM Analysis Service
│   ├── topic-tracking/          # 4.4 Topic Tracking Service
│   ├── summary-generation/      # 4.5 Summary Generation Service
│   ├── task-management/         # 4.6 Task Management Service
│   ├── calendar-sync/           # 4.7 Calendar Sync Service
│   └── bff/                     # 4.8 BFF Layer
├── frontend/                    # 4.9 Vue 3 + Tailwind + TypeScript
├── db/
│   └── migrations/              # SQL migrations (pgvector schema)
└── docs/                        # Additional architectural documentation
```

---

*This document is the authoritative reference for the vision, architecture, and technical direction of mail-manager. All implementation decisions should be validated against the objectives and constraints defined here.*
