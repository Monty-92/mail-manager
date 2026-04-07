---
description: "Use when writing or editing Dockerfiles or docker-compose.yml. Covers multi-stage builds, uv in Docker, health checks, non-root users, and layer caching."
applyTo: "**/Dockerfile, docker-compose.yml"
---
# Docker Guidelines

## Dockerfiles (Python services)
- Multi-stage build: `builder` stage installs deps with uv → `runtime` stage copies only what's needed
- Base image: `python:3.12-slim`
- Copy `pyproject.toml` and `uv.lock` first for layer caching
- Install uv in builder: `COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv`
- Use `uv sync --frozen --no-dev` for production installs
- Create non-root user in runtime stage: `RUN useradd -r -s /bin/false appuser && USER appuser`
- Include `HEALTHCHECK` instruction: `HEALTHCHECK CMD curl -f http://localhost:8000/health || exit 1`
- Expose the correct port: `EXPOSE 8000`

## Dockerfiles (Frontend)
- Multi-stage: Node build stage → nginx serve stage
- Use `node:22-slim` for build, `nginx:alpine` for serve
- Copy `package.json` and `package-lock.json` first for layer caching

## docker-compose.yml
- All services defined in a single `docker-compose.yml` at repo root
- Use `depends_on` with `condition: service_healthy` for dependency ordering
- Postgres, Redis, Ollama are infrastructure services
- Python services mount `.env` for configuration
- Use named volumes for persistent data (postgres, ollama models)
- Service names match directory names: `ingestion`, `preprocessing`, `bff`, etc.

## Volume Preservation (CRITICAL)
- **NEVER run `docker compose down -v`** unless the user explicitly requests a full data wipe
- Ollama volume (`ollamadata`) contains large models (~5 GB+) that take a long time to re-download
- Postgres volume (`pgdata`) contains all application data — prefer `DROP TABLE` / re-run migrations over wiping the volume
- To reset the database without losing Ollama models: stop only postgres, remove its volume, restart, re-run migrations
- To rebuild service images: `docker compose up -d --build <service>` (preserves all volumes)
- To restart services: `docker compose restart <service>` (preserves state and volumes)
- Acceptable alternatives for a clean DB reset:
  - `docker compose exec postgres psql -U mailmanager -d mailmanager -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"` then re-run migrations
  - Or selectively `TRUNCATE` tables

## Post-Change Rebuild (REQUIRED)

After every phase of code changes, **always rebuild and restart the affected application services**. Do not skip this step — containers run the previously-built image until rebuilt.

### Which services to rebuild

| Changed area | Services to rebuild |
|---|---|
| `services/ingestion/` | `ingestion` |
| `services/preprocessing/` | `preprocessing` |
| `services/llm-analysis/` | `llm-analysis` |
| `services/topic-tracking/` | `topic-tracking` |
| `services/summary-generation/` | `summary-generation` |
| `services/task-management/` | `task-management` |
| `services/calendar-sync/` | `calendar-sync` |
| `services/bff/` | `bff` |
| `frontend/` | `frontend` |
| `db/migrations/` | Run `make migrate` (no rebuild needed) |
| Multiple services | List them all in one command |

### Services NEVER to rebuild unnecessarily

- `ollama` — contains multi-GB models; rebuilding wipes them and triggers re-download
- `postgres` — rebuilding drops the `pgdata` volume unless `down` is avoided
- `redis` — stateless cache; only restart if config changes

### Rebuild command pattern

```bash
# Rebuild only the affected services (example: ingestion + bff changed)
docker compose up -d --build ingestion bff

# Rebuild all application services at once (never include ollama/postgres/redis)
docker compose up -d --build ingestion preprocessing llm-analysis topic-tracking summary-generation task-management calendar-sync bff frontend
```

- Always use `up -d --build <services>` — this rebuilds images **and** replaces the running containers in one step without touching volumes.
- After rebuilding, verify with: `docker compose ps` (all rebuilt services should be `running`/`healthy`).
