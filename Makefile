.PHONY: up down build logs migrate test lint clean

# ─── Docker Compose ───
up:
	docker compose up

up-d:
	docker compose up -d

down:
	docker compose down

build:
	docker compose build

logs:
	docker compose logs -f

# ─── Database ───
migrate:
	@for f in db/migrations/*.sql; do \
		echo "Running $$f..."; \
		docker compose exec -T postgres psql -U mailmanager -d mailmanager -f /migrations/$$(basename $$f); \
	done

# ─── Testing ───
test:
	@for svc in services/*/; do \
		echo "Testing $$(basename $$svc)..."; \
		cd $$svc && uv run pytest && cd ../..; \
	done

test-svc:
	cd services/$(svc) && uv run pytest

# ─── Linting ───
lint:
	@for svc in services/*/; do \
		echo "Linting $$(basename $$svc)..."; \
		cd $$svc && uv run ruff check . && cd ../..; \
	done
	cd frontend && npm run lint

lint-svc:
	cd services/$(svc) && uv run ruff check .

# ─── Cleanup ───
clean:
	docker compose down -v --remove-orphans
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
