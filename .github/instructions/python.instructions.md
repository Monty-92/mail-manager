---
description: "Use when writing or editing Python files. Covers FastAPI patterns, async conventions, Pydantic models, uv dependency management, ruff formatting, and structlog logging."
applyTo: "**/*.py"
---
# Python Coding Guidelines

## FastAPI Patterns
- Use `async def` for all endpoints and I/O-bound functions
- Return Pydantic response models, never raw dicts
- Use dependency injection for DB sessions, config, and service clients
- Register routers in `main.py` with versioned prefixes where applicable

## Pydantic
- Use Pydantic v2 (`BaseModel` for schemas, `BaseSettings` for config)
- Config class per service in `config.py`, loaded from environment variables
- Use `model_validator` over `@validator` (v2 style)

## Package Management
- Use `uv` for all dependency management (`uv add`, `uv run`)
- Each service has its own `pyproject.toml` and `uv.lock`
- Pin major versions in dependencies

## Code Quality
- `ruff` for linting and formatting (line length 120)
- Type hints on all function signatures and return types
- Use `uuid7()` for generating new primary keys
- Imports ordered: stdlib → third-party → local (ruff isort handles this)

## Logging
- Use `structlog` for structured JSON logging
- Log at appropriate levels: `debug` for internals, `info` for operations, `error` for failures
- Include contextual fields: `service`, `email_id`, `operation`

## Testing
- `pytest` + `pytest-asyncio` for async tests
- Fixtures in `conftest.py` at the test directory root
- Use `httpx.AsyncClient` for testing FastAPI endpoints
- Mock external services (Gmail API, Ollama) in tests

## Error Handling
- Raise `HTTPException` with appropriate status codes in endpoints
- Use custom exception classes for domain errors
- Always return `{"detail": "message"}` shape for errors

## Database
- Use `asyncpg` for async Postgres connections
- Use connection pools, never create connections per request
- Parameterize all queries to prevent SQL injection
