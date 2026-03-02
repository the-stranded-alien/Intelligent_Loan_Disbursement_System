.PHONY: up down build logs migrate seed test clean ps shell-api shell-agent shell-notif

# ── Docker Compose ─────────────────────────────────────────────────────────────

up:
	docker compose up -d

up-watch:
	docker compose up --watch

down:
	docker compose down

build:
	docker compose build

rebuild:
	docker compose build --no-cache

logs:
	docker compose logs -f

ps:
	docker compose ps

clean:
	docker compose down -v --remove-orphans
	docker system prune -f

# ── Database ───────────────────────────────────────────────────────────────────

migrate:
	docker compose exec backend-api alembic upgrade head

migrate-down:
	docker compose exec backend-api alembic downgrade -1

migrate-status:
	docker compose exec backend-api alembic current

migrate-new:
	@read -p "Migration message: " msg; \
	docker compose exec backend-api alembic revision --autogenerate -m "$$msg"

# ── RAG Seeding ────────────────────────────────────────────────────────────────

seed:
	docker compose exec agent-service python -m scripts.seed_rag

# ── Testing ────────────────────────────────────────────────────────────────────

test:
	docker compose exec backend-api pytest tests/ -v
	docker compose exec agent-service pytest tests/ -v
	docker compose exec notification-service pytest tests/ -v

test-api:
	docker compose exec backend-api pytest tests/ -v

test-agent:
	docker compose exec agent-service pytest tests/ -v

test-notif:
	docker compose exec notification-service pytest tests/ -v

# ── Shell Access ───────────────────────────────────────────────────────────────

shell-api:
	docker compose exec backend-api bash

shell-agent:
	docker compose exec agent-service bash

shell-notif:
	docker compose exec notification-service bash

shell-db:
	docker compose exec postgres psql -U $${POSTGRES_USER:-loan_user} -d $${POSTGRES_DB:-loan_db}

shell-redis:
	docker compose exec redis redis-cli
