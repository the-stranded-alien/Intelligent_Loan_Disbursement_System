---
description: Run the full test suite across all services and report results
allowed-tools: Bash(docker compose exec:*), Bash(docker compose run:*)
---

## Context

- Test files in backend-api: !`find backend-api -name "test_*.py" 2>/dev/null | head -20 || echo "No tests found"`
- Test files in agent-service: !`find agent-service -name "test_*.py" 2>/dev/null | head -20 || echo "No tests found"`
- Test files in notification-service: !`find notification-service -name "test_*.py" 2>/dev/null | head -20 || echo "No tests found"`

## Your task

Run the full test suite for the Intelligent Loan Disbursement System and produce a unified report.

### Steps

1. **Check services are running** — tests require postgres and redis. If not running:
   ```
   docker compose up -d postgres redis
   ```

2. **Run backend-api tests**:
   ```
   docker compose exec backend-api python -m pytest backend-api/tests/ -v --tb=short 2>&1
   ```

3. **Run agent-service tests** (mock all LLM and external API calls):
   ```
   docker compose exec agent-service python -m pytest agent-service/tests/ -v --tb=short 2>&1
   ```

4. **Run notification-service tests** (mock Twilio/SendGrid):
   ```
   docker compose exec notification-service python -m pytest notification-service/tests/ -v --tb=short 2>&1
   ```

5. **Run frontend type check** (if frontend is scaffolded):
   ```
   docker compose exec frontend npx tsc --noEmit 2>&1
   ```

6. **Aggregate results** in a formatted summary:
   ```
   ┌─────────────────────────────────────────────────┐
   │                 TEST RESULTS                    │
   ├──────────────────────┬────────┬───────┬─────────┤
   │ Service              │ Passed │ Failed│ Skipped │
   ├──────────────────────┼────────┼───────┼─────────┤
   │ backend-api          │   12   │   0   │    1    │
   │ agent-service        │    8   │   2   │    0    │
   │ notification-service │    5   │   0   │    0    │
   │ frontend (tsc)       │   ✓    │       │         │
   └──────────────────────┴────────┴───────┴─────────┘
   ```

7. **For any failures**, show:
   - The failing test name
   - The error message
   - A suggested fix

8. **If no tests exist yet** for a service, suggest running `/test-agent <name>` to generate agent tests, and offer to scaffold basic test files.
