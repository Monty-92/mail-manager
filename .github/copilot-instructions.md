# mail-manager — Copilot Workspace Instructions

## Project

mail-manager is a modular email-intelligence and personal productivity engine. See [PROJECT_OVERVIEW.md](../PROJECT_OVERVIEW.md) for full architecture, data model, and objectives.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.12, FastAPI, uv (package/env manager) |
| Frontend | Vue 3 (Composition API), TypeScript (strict), Tailwind CSS, npm |
| Database | PostgreSQL 16 + pgvector (vector(768), nomic-embed-text) |
| LLM | Ollama (Docker container), default model llama3.1:8b |
| Email providers | Gmail API, Microsoft Graph API (MSAL) |
| Calendar providers | Google Calendar API, Microsoft Graph Calendar API |
| Message broker | Redis (pub/sub + caching) |
| Containers | Docker + Docker Compose |

## Architecture

- **Microservice architecture** with 8 Python services + 1 Vue frontend + BFF layer
- Each service: own `Dockerfile`, own `uv` project (`pyproject.toml`), shared PostgreSQL
- Service communication: HTTP for request/response, Redis pub/sub for event-driven pipelines
- BFF layer aggregates internal services and exposes versioned REST API (`/api/v1/`)
- All services expose `GET /health` returning `{"status": "ok"}`
- Full stack runs with `docker compose up`

## Code Style — Python

- Use `ruff` for linting and formatting (line length 120)
- Type hints on all function signatures
- Async-first: use `async def` for FastAPI endpoints and I/O-bound operations
- Pydantic v2 models for all request/response schemas and config (`BaseSettings`)
- Use `uuid7` for new primary keys
- Imports: stdlib → third-party → local (ruff handles this)
- Tests: `pytest` + `pytest-asyncio`, fixtures in `conftest.py`

## Code Style — TypeScript / Vue

- Vue 3 Composition API with `<script setup lang="ts">`
- TypeScript strict mode (`strict: true` in tsconfig)
- Tailwind CSS utility classes; avoid custom CSS unless necessary
- Pinia for state management
- Vue Router for navigation
- Component naming: PascalCase files, multi-word names (e.g., `EmailBrowser.vue`)

## Code Style — SQL

- Use `UUID` primary keys with `gen_random_uuid()` default
- `TIMESTAMPTZ` for all timestamps, default `now()`
- pgvector columns: `vector(768)` (nomic-embed-text embedding dimension)
- Migrations are sequential numbered SQL files in `db/migrations/`
- Always include `IF NOT EXISTS` / `IF EXISTS` guards

## Code Style — Docker

- Multi-stage builds: build stage (install deps with uv) → slim runtime stage
- Use `python:3.12-slim` as base
- Copy `uv.lock` and `pyproject.toml` first for layer caching
- Include `HEALTHCHECK` instruction in every service Dockerfile
- Never run containers as root in production stages

## Commands

| Task | Command |
|------|---------|
| Start full stack | `make up` or `docker compose up` |
| Start in background | `make up-d` |
| Stop all services | `make down` |
| Run migrations | `make migrate` |
| Run all tests | `make test` |
| Test one service | `make test-svc svc=<name>` |
| Lint all | `make lint` |
| Start specific service | `docker compose up <service-name>` |
| Run frontend dev | `cd frontend && npm run dev` |
| Create feature branch | `git checkout main && git pull && git checkout -b type/description` |
| Open PR | `gh pr create --title "type(scope): subject" --body "..."` |
| Merge PR (rebase) | `gh pr merge --rebase --delete-branch` |
| Clean up after merge | `git checkout main && git pull && git branch -d type/description` |

## Git Workflow

- **Branches**: all work on feature branches, never commit directly to `main`
- **Branch naming**: `type/description` (e.g., `feat/add-preprocessing-service`, `fix/oauth-refresh`)
- **Commits**: [Conventional Commits](https://www.conventionalcommits.org/) required — prefixes: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `style`, `build`, `perf`, `ci`
- **PRs**: all changes reach `main` through pull requests with descriptive bodies
- **Merge strategy**: rebase and merge only (linear history, no merge commits)
- **Agent behavior**: proactively prompt user to commit/push at natural breakpoints (tests passing, phase complete, before context switch)
- See `.github/instructions/git.instructions.md` for full details

## Conventions

- Environment variables: defined in `.env`, loaded via Pydantic `BaseSettings`
- Secrets (OAuth tokens, API keys): never committed; use `.env` (gitignored) and `.env.example` as template
- Service-to-service calls: use Docker Compose service names as hostnames (e.g., `http://ingestion:8000`)
- Redis channels: `mailmanager.<event_name>` (e.g., `mailmanager.email.new`)
- API responses: always return JSON with consistent error shape `{"detail": "message"}`
- Logging: structured JSON logs via `structlog`

## Authentication Architecture

- **Password hashing**: `bcrypt` directly (not passlib) — `bcrypt.hashpw` / `bcrypt.checkpw`
- **Login flow**: two-step — step 1 validates password and returns `totp_required: true`, step 2 validates TOTP code and returns JWT
- **JWT sessions**: `pyjwt` with `HS256`, 24-hour expiry, payload `{"sub": user_id, "exp": ...}`
- **TOTP 2FA**: `pyotp` + `qrcode`, setup via `/auth/setup-qr` (public path for first-time setup)
- **OAuth**: Google (google-auth-oauthlib with PKCE) and Microsoft (MSAL ConfidentialClientApplication)
- **Redirect URI**: both providers use `http://localhost:3000/auth/callback` (frontend handles callback)
- **Frontend auth**: Vue Router `beforeEach` guard checks auth store, redirects unauthenticated users to `/login`

## Living Documents

This project maintains **living documents** that must stay current:

- `PROJECT_OVERVIEW.md` — Authoritative architecture reference
- `README.md` — Quick-start guide and prerequisites
- `docs/` — Additional architecture and API documentation

**Rules:**
1. When adding/removing/modifying a service, update `PROJECT_OVERVIEW.md` section 4 (Architecture) and section 8 (Repository Structure)
2. When changing the data model, update `PROJECT_OVERVIEW.md` section 5
3. When changing build/run commands, update `README.md`
4. When in doubt, run the `/maintain-living-docs` skill

## Copilot Configuration Self-Maintenance

The `.github/` directory contains Copilot customization files that must stay aligned with the codebase:

- `.github/copilot-instructions.md` — This file (workspace instructions)
- `.github/instructions/*.instructions.md` — File-specific coding guidelines
- `.github/skills/*/SKILL.md` — On-demand workflow skills
- `.github/agents/*.agent.md` — Custom agent definitions

**Rules:**
1. When tech stack or conventions change, update this file and relevant `.instructions.md` files
2. When adding a new service pattern, update the `add-service` skill
3. When adding new document types, update the `maintain-living-docs` skill
4. When in doubt, run the `/maintain-copilot-config` skill
5. After significant refactors, review all `.github/` files for staleness
