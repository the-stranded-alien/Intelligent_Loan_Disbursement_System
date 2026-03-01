---
description: Tail logs from a specific Docker service or show recent errors across all services
argument-hint: "backend-api | agent-service | agent-worker | notification-service | notification-worker | celery-beat | frontend | postgres | redis | all | errors"
allowed-tools: Bash(docker compose logs:*)
---

## Context

- Running containers: !`docker ps --format "{{.Names}}\t{{.Status}}" 2>/dev/null || echo "Docker not running"`
- Argument: $ARGUMENTS

## Your task

Show logs for the Loan system services based on: **$ARGUMENTS**

Valid service names: `backend-api`, `agent-service`, `agent-worker`, `notification-service`, `notification-worker`, `celery-beat`, `frontend`, `postgres`, `redis`

Special modes:
- `all` — Show last 30 lines from every service
- `errors` — Show only ERROR/CRITICAL/Exception lines across all services

### If no argument or `all`
Show last 30 lines from all services:
```
docker compose logs --tail=30 --no-log-prefix 2>&1 | grep -E "^[A-Za-z-]+" | head -200
```
Highlight lines containing ERROR, CRITICAL, or Exception in the output summary.

### If `errors`
Filter only error lines across all services:
```
docker compose logs --tail=200 2>&1 | grep -iE "error|critical|exception|traceback|failed" | tail -50
```
Group by service and show the most recent error per service.

### If a specific service name
Tail 50 lines with timestamps:
```
docker compose logs --tail=50 --timestamps <service-name>
```

### After showing logs
- If there are ERROR lines, highlight them and suggest possible fixes based on common issues:
  - `Connection refused` on Postgres → Postgres isn't ready, run `/dev`
  - `Redis connection error` → Redis isn't running
  - `ModuleNotFoundError` → Missing dependency in requirements.txt
  - `alembic.util.exc.CommandError` → Run `/migrate`
  - `ANTHROPIC_API_KEY` missing → Check .env file
- If no errors found, report that services look healthy.
