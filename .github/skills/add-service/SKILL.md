---
name: add-service
description: "Step-by-step guide for adding a new Python microservice to mail-manager. Use when: creating a new backend service, scaffolding a new FastAPI microservice, or expanding the service architecture."
---

# Add a New Microservice

## When to Use
- Creating a new backend service from scratch
- Expanding the architecture with a new capability

## Procedure

### 1. Create Service Directory
```
services/<service-name>/
├── Dockerfile
├── pyproject.toml
├── src/
│   └── <service_name>/
│       ├── __init__.py
│       ├── main.py          # FastAPI app + health endpoint
│       └── config.py         # Pydantic BaseSettings
└── tests/
    ├── __init__.py
    └── conftest.py
```

### 2. Create `pyproject.toml`
```toml
[project]
name = "<service-name>"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.34.0",
    "pydantic-settings>=2.7.0",
    "structlog>=24.4.0",
    "asyncpg>=0.30.0",
    "httpx>=0.28.0",
]

[tool.ruff]
line-length = 120

[tool.pytest.ini_options]
asyncio_mode = "auto"
```

### 3. Create `main.py`
- Import FastAPI, create app instance with `lifespan` context manager
- Add `GET /health` returning `{"status": "ok"}`
- Register routers for service-specific endpoints
- Configure structlog in the lifespan startup phase

### 4. Create `config.py`
- Pydantic `BaseSettings` class with service-specific env vars
- Always include: `DATABASE_URL`, `REDIS_URL`, `SERVICE_NAME`

### 5. Create `Dockerfile`
- Multi-stage build (builder + runtime)
- Base: `python:3.12-slim`
- Install deps with uv in builder stage
- Non-root user in runtime stage
- Health check instruction

### 6. Add to `docker-compose.yml`
- Add service definition with build context pointing to `services/<name>/`
- Add `depends_on` for postgres and redis (with health conditions)
- Map port (use next available: 8001, 8002, etc.)
- Add environment variables from `.env`
- **Do NOT use `docker compose down -v`** to test the new service — use `docker compose up -d --build <service>` to avoid wiping Ollama models and DB data

### 7. Update Living Documents
- Run `/maintain-living-docs` to update PROJECT_OVERVIEW.md and README.md
- Run `/maintain-copilot-config` if the new service introduces new patterns

### 8. Create Initial Migration (if needed)
- Add migration file in `db/migrations/` for any new tables
- Follow sequential numbering convention
- Include `IF NOT EXISTS` guards

### 9. Verify
- `docker compose build <service-name>` succeeds
- `docker compose up <service-name>` starts and health check passes
- `cd services/<service-name> && uv run pytest` passes
