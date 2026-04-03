FROM python:3.12-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app
COPY pyproject.toml uv.lock* ./
RUN uv sync --frozen --no-dev --no-install-project 2>/dev/null || uv sync --no-dev --no-install-project

COPY src/ src/
RUN uv sync --frozen --no-dev 2>/dev/null || uv sync --no-dev

FROM python:3.12-slim AS runtime

RUN useradd -r -s /bin/false appuser
WORKDIR /app

COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/src /app/src

ENV PATH="/app/.venv/bin:$PATH"
USER appuser

EXPOSE 8002
HEALTHCHECK --interval=10s --timeout=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8002/health')" || exit 1

CMD ["uvicorn", "preprocessing.main:app", "--host", "0.0.0.0", "--port", "8002"]
