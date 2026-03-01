---
description: Show the health and status of the entire system — services, pipeline metrics, Redis streams, and DB
allowed-tools: Bash(docker compose ps:*), Bash(curl:*), Bash(docker compose exec:*)
---

## Context

- Container status: !`docker compose ps 2>/dev/null || echo "Docker Compose not running"`
- Backend health: !`curl -s http://localhost:8000/health 2>/dev/null || echo "Backend API unreachable"`

## Your task

Show a comprehensive health and status dashboard for the Intelligent Loan Disbursement System.

### 1. Service Health

Check all 9 services and show a status table:
```
Service               | Status    | Port  | Health
----------------------|-----------|-------|-------
postgres              | ✓ running | 5432  | OK
redis                 | ✓ running | 6379  | OK
backend-api           | ✓ running | 8000  | GET /health → 200
agent-service         | ✓ running | 8001  | GET /health → 200
agent-worker          | ✓ running | —     | celery inspect ping
notification-service  | ✓ running | 8002  | GET /health → 200
notification-worker   | ✓ running | —     | celery inspect ping
celery-beat           | ✓ running | —     | process alive
frontend              | ✓ running | 3000  | GET / → 200
```

Run these in parallel:
```bash
curl -s http://localhost:8000/health
curl -s http://localhost:8001/health
curl -s http://localhost:8002/health
curl -s http://localhost:3000
docker compose exec redis redis-cli PING
docker compose exec postgres psql -U loan_user -d loan_db -c "SELECT 1;"
```

### 2. Pipeline Metrics

```
curl -s http://localhost:8000/analytics/pipeline | python3 -m json.tool
```

Show:
- Total applications (all time / last 24h)
- By stage: how many at each of the 9 nodes
- Pending HITL reviews
- Completion rate, rejection rate
- Average pipeline time

### 3. Redis Streams Backlog

Check pending message counts on all event streams:
```
docker compose exec redis redis-cli XLEN application.created
docker compose exec redis redis-cli XLEN node.completed
docker compose exec redis redis-cli XLEN hitl.requested
docker compose exec redis redis-cli XLEN pipeline.completed
docker compose exec redis redis-cli XLEN pipeline.rejected
```

Flag any stream with > 100 pending messages as a potential bottleneck.

### 4. Celery Workers

```
docker compose exec agent-worker celery -A worker.celery_app inspect active
docker compose exec notification-worker celery -A worker.celery_app inspect active
```

Show active tasks per worker and queue depths.

### 5. Summary

End with a one-line health verdict:
- ALL SYSTEMS OPERATIONAL
- DEGRADED — list affected services
- DOWN — list what's failing and suggest `/dev` to restart
