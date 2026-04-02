# mail-manager — Project Overview

## 1. Vision

**mail-manager** is a modular, extensible email-intelligence engine that ingests Gmail emails, analyzes them using locally hosted LLMs, and maintains *living documents* that always reflect the current state of tasks, topics, and daily summaries.

It is designed as a reusable intelligence layer that can be embedded into a broader personal knowledge management (PKM) system and expanded to additional data sources such as Google Calendar, Google Tasks, and Notion.

> **Core mission:** transform raw communication streams into structured, queryable, and continuously updated knowledge — entirely on local infrastructure, with no paid cloud services.

---

## 2. Core Objectives

| # | Objective |
|---|-----------|
| 1 | Ingest both historical and new Gmail emails via the Gmail API |
| 2 | Convert emails to Markdown for readability and LLM-friendliness |
| 3 | Store all data (emails, summaries, tasks, topics) in PostgreSQL |
| 4 | Use `pgvector` for embeddings and semantic search |
| 5 | Group emails by thread and semantic topic |
| 6 | Generate daily summaries (morning + evening) |
| 7 | Maintain evolving topic snapshots |
| 8 | Detect junk mail while surfacing potentially valuable promotions |
| 9 | Extract action items and sync them bidirectionally with Google Tasks |
| 10 | Produce and update Markdown-based living documents |
| 11 | Provide a modern web UI for browsing insights and interacting with the system |

---

## 3. Technical Constraints

The system relies **exclusively** on free and open-source technologies. No paid cloud services or proprietary LLM APIs are permitted.

| Category | Technology |
|----------|-----------|
| Containerization | [Docker](https://www.docker.com/) |
| Orchestration | [Docker Compose](https://docs.docker.com/compose/) |
| Python environments | [uv](https://github.com/astral-sh/uv) by Astral |
| Database | [PostgreSQL](https://www.postgresql.org/) + [pgvector](https://github.com/pgvector/pgvector) |
| Local LLM inference | [Llama.cpp](https://github.com/ggerganov/llama.cpp) / [Ollama](https://ollama.com/) |
| Backend framework | [FastAPI](https://fastapi.tiangolo.com/) (or equivalent free framework) |
| Frontend | [Vue 3](https://vuejs.org/) + [Tailwind CSS](https://tailwindcss.com/) + TypeScript |
| Email integration | Gmail API (free tier) |
| Task integration | Google Tasks API (free tier) |

**Guiding principles:** reproducibility, local execution, and modularity. Every developer must be able to run the full stack with `docker compose up`.

---

## 4. Architecture Overview

mail-manager follows a **microservice architecture** with a dedicated **Backend-for-Frontend (BFF)** layer that shields the UI from internal service complexity.

```
┌─────────────────────────────────────────────────────────────────┐
│                        Frontend (Vue 3)                         │
└──────────────────────────────┬──────────────────────────────────┘
                               │ HTTP / WebSocket
┌──────────────────────────────▼──────────────────────────────────┐
│                       BFF Layer (FastAPI)                        │
└──┬──────────┬──────────┬──────────┬──────────┬──────────┬───────┘
   │          │          │          │          │          │
   ▼          ▼          ▼          ▼          ▼          ▼
Ingest  Preprocess  LLM Analysis  Topic   Summary   Task Mgmt
Service  Service     Service    Tracking  Service   Service
   │          │          │          │          │          │
   └──────────┴──────────┴──────────┴──────────┴──────────┘
                               │
                    ┌──────────▼──────────┐
                    │  PostgreSQL + pgvector │
                    └─────────────────────┘
```

### 4.1 Ingestion Service

- Connects to the Gmail API using OAuth 2.0
- Fetches both historical and new/streaming emails
- Converts raw email payloads to clean Markdown
- Stores email content, metadata, and embeddings in Postgres
- Deduplicates by Gmail message ID

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

- Extracts tasks and action items from emails
- Stores tasks in Postgres with source-email and topic relationships
- Syncs **bidirectionally** with Google Tasks API
- Maintains sync metadata (external task ID, last-sync timestamp, conflict state)

### 4.7 BFF Layer

- Provides a clean, versioned REST (and optional GraphQL) API for the UI
- Aggregates and shapes data from multiple internal services
- Handles user authentication and permission checks
- Rate-limits and caches responses where appropriate

### 4.8 Frontend (Vue 3 + Tailwind CSS + TypeScript)

- Renders living documents (tasks, topics, summaries) in Markdown
- Displays dashboards with filtering and search
- Provides email-insight views and topic drill-downs
- Optional: Chrome extension integration for in-browser context

### 4.9 Orchestration

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
| `gmail_message_id` | TEXT UNIQUE | Gmail message ID (dedup key) |
| `thread_id` | TEXT | Gmail thread ID |
| `sender` | TEXT | Sender email address |
| `recipients` | TEXT[] | To / CC / BCC addresses |
| `subject` | TEXT | Email subject line |
| `received_at` | TIMESTAMPTZ | Received timestamp |
| `labels` | TEXT[] | Gmail labels |
| `markdown_body` | TEXT | Full email body as Markdown |
| `embedding` | vector(1536) | Semantic embedding (pgvector) |
| `created_at` | TIMESTAMPTZ | Row creation timestamp |

Relationships: many-to-many with `topics` and `tasks`.

### 5.2 `topics`

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID PK | Internal identifier |
| `name` | TEXT | Human-readable topic name |
| `embedding` | vector(1536) | Semantic embedding |
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
| `embedding` | vector(1536) | Semantic embedding |
| `diff_hash` | TEXT | SHA hash for change detection |
| `created_at` | TIMESTAMPTZ | Row creation timestamp |

Relationships: many-to-many with `topics`.

### 5.4 `tasks`

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID PK | Internal identifier |
| `description` | TEXT | Task description |
| `status` | TEXT | `pending`, `in_progress`, `done`, `cancelled` |
| `source_email_id` | UUID FK → `emails` | Email the task was extracted from |
| `google_task_id` | TEXT | External Google Tasks ID |
| `last_synced_at` | TIMESTAMPTZ | Last bidirectional sync timestamp |
| `created_at` | TIMESTAMPTZ | Row creation timestamp |

Relationships: many-to-many with `topics`.

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

- **Google Calendar ingestion** — ingest events and correlate with email threads and tasks
- **Notion integration** — push living documents and task states to Notion pages
- **Additional communication channels** — Slack, Microsoft Teams, SMS
- **Knowledge-graph expansion** — build an entity graph (people, organizations, projects) across all data sources
- **Multi-agent orchestration** — coordinate specialized LLM agents for research, drafting, and scheduling

New services will follow the same patterns: a dedicated Postgres schema, a `uv`-managed Python environment, a Dockerfile, and a service definition in `docker-compose.yml`.

---

## 8. Repository Structure (target)

```
mail-manager/
├── PROJECT_OVERVIEW.md          # This file
├── README.md                    # Quick-start guide
├── docker-compose.yml           # Full stack definition
├── services/
│   ├── ingestion/               # 4.1 Ingestion Service
│   ├── preprocessing/           # 4.2 Preprocessing & Normalization Service
│   ├── llm-analysis/            # 4.3 LLM Analysis Service
│   ├── topic-tracking/          # 4.4 Topic Tracking Service
│   ├── summary-generation/      # 4.5 Summary Generation Service
│   ├── task-management/         # 4.6 Task Management Service
│   └── bff/                     # 4.7 BFF Layer
├── frontend/                    # 4.8 Vue 3 + Tailwind + TypeScript
├── db/
│   └── migrations/              # SQL migrations (pgvector schema)
└── docs/                        # Additional architectural documentation
```

---

*This document is the authoritative reference for the vision, architecture, and technical direction of mail-manager. All implementation decisions should be validated against the objectives and constraints defined here.*
