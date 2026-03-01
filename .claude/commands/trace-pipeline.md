---
description: Trace a loan application through the full 9-node LangGraph pipeline and show decision at each node
argument-hint: "<application_id> | new"
allowed-tools: Bash(docker compose exec:*), Bash(curl:*)
---

## Context

- Running services: !`docker ps --format "{{.Names}}\t{{.Status}}" 2>/dev/null | grep -E "backend|agent" || echo "Services not running"`
- Argument: $ARGUMENTS

## Your task

Trace a loan application through the pipeline.

### If argument is `new` or empty — create a test application

1. POST a new application to the API:
   ```
   curl -s -X POST http://localhost:8000/apply \
     -H "Content-Type: application/json" \
     -d '{
       "applicant_name": "Trace Test User",
       "pan_number": "ABCDE1234F",
       "phone": "+919876543210",
       "email": "trace@example.com",
       "monthly_income": 80000,
       "loan_amount": 300000,
       "loan_purpose": "business expansion",
       "channel": "web"
     }' | python3 -m json.tool
   ```
2. Note the returned `application_id` and proceed to trace it.

### If argument is an `application_id` — trace existing application

1. Fetch the current pipeline status:
   ```
   curl -s http://localhost:8000/status/<application_id> | python3 -m json.tool
   ```

2. Fetch audit logs from the DB:
   ```
   docker compose exec postgres psql -U loan_user -d loan_db \
     -c "SELECT node_name, status, decision, reasoning, created_at FROM audit_logs WHERE application_id='<application_id>' ORDER BY created_at ASC;"
   ```

3. Fetch LangGraph checkpoint state:
   ```
   docker compose exec postgres psql -U loan_user -d loan_db \
     -c "SELECT thread_id, checkpoint_ns, channel_values FROM checkpoints WHERE thread_id='<application_id>' ORDER BY step ASC;"
   ```

4. Display a formatted timeline showing each of the 9 nodes:
   ```
   Node 1: Lead Capture         [✓ COMPLETED | ✗ FAILED | ⏳ PENDING | 🔴 HITL]
   Node 2: Lead Qualification   ...
   Node 3: Identity Verification ...
   Node 4: Credit Assessment    ...
   Node 5: Fraud Detection      ...
   Node 6: Compliance           ...
   Node 7: Document Collection  ...
   Node 8: Sanction Processing  ...
   Node 9: Disbursement         ...
   ```
   For each completed node show: status, decision, and the LLM's key reasoning (1-2 sentences).

5. If a node is in HITL state, show the HITL review queue entry.

6. If the pipeline has failed, show the error and which node it failed at.

### Notes
- If services are not running, tell the user to run `/dev` first.
- If application_id is not found, say so clearly.
