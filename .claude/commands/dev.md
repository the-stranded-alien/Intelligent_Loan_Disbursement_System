---
description: Start the full Docker Compose dev environment with health checks
allowed-tools: Bash(docker compose up:*), Bash(docker compose ps:*), Bash(docker compose logs:*), Bash(docker ps:*)
---

## Context

- Docker Compose file: !`cat docker-compose.yml 2>/dev/null | head -40 || echo "docker-compose.yml not found"`
- Running containers: !`docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null`
- .env exists: !`test -f .env && echo "YES" || echo "NO — copy .env.example first"`

## Your task

Start the Intelligent Loan Disbursement System local dev environment.

### Steps

1. **Verify prerequisites**
   - Check `.env` exists. If not, warn the user and stop — they must `cp .env.example .env` and fill in secrets.
   - Check Docker daemon is running (`docker ps`). If not, tell user to start Docker Desktop and stop.

2. **Bring up infrastructure first** (postgres + redis)
   ```
   docker compose up -d postgres redis
   ```
   Wait up to 30 seconds for Postgres to be ready (check with `docker compose ps`).

3. **Run migrations**
   ```
   docker compose run --rm backend-api alembic upgrade head
   ```

4. **Bring up all remaining services**
   ```
   docker compose up -d
   ```

5. **Health check** — poll `docker compose ps` and report status of every service:
   - postgres
   - redis
   - backend-api (port 8000 — try `curl -s http://localhost:8000/health`)
   - agent-service (port 8001)
   - notification-service (port 8002)
   - agent-worker
   - notification-worker
   - celery-beat
   - frontend (port 3000)

6. **Report** a clean summary table of what's up, what's down, and the URLs to open:
   - App: http://localhost:3000
   - API docs: http://localhost:8000/docs
   - Agent service: http://localhost:8001/docs

If any service fails to start, show the last 20 lines of its logs to help debug.
