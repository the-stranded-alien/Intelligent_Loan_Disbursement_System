---
description: Run Alembic database migrations for backend-api
argument-hint: "up | down | status | new <message>"
allowed-tools: Bash(docker compose exec:*), Bash(docker compose run:*)
---

## Context

- Migration files: !`find backend-api/db/migrations/versions -name "*.py" 2>/dev/null | sort | tail -10 || echo "No migrations found"`
- Current migration head: !`docker compose exec backend-api alembic current 2>/dev/null || echo "Service not running"`
- Pending migrations: !`docker compose exec backend-api alembic history --indicate-current 2>/dev/null | head -20 || echo ""`

## Your task

Manage Alembic database migrations based on: **$ARGUMENTS**

If no argument given, default to `up` (upgrade to head).

### Commands

**`up`** — Apply all pending migrations:
```
docker compose exec backend-api alembic upgrade head
```
Then show current revision.

**`down`** — Rollback one migration:
Confirm with the user before running:
```
docker compose exec backend-api alembic downgrade -1
```
Then show current revision.

**`status`** — Show current migration state:
```
docker compose exec backend-api alembic current
docker compose exec backend-api alembic history --indicate-current
```

**`new <message>`** — Generate a new migration file:
```
docker compose exec backend-api alembic revision --autogenerate -m "<message>"
```
Then show the generated file path and its content so the user can review it.

### Rules
- For `down`, always ask for confirmation before rolling back — data loss is possible.
- After any migration, print the current head revision.
- If the backend-api container is not running, tell the user to run `/dev` first.
