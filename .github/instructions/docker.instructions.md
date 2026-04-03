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
