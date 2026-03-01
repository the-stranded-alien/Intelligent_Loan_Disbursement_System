---
description: Process a Human-In-The-Loop (HITL) review — approve or reject an application pending RM review
argument-hint: "<application_id> approve | <application_id> reject [reason]"
allowed-tools: Bash(curl:*), Bash(docker compose exec:*)
---

## Context

- HITL queue: !`curl -s http://localhost:8000/rm/queue 2>/dev/null | python3 -m json.tool | head -60 || echo "Backend not running — start with /dev"`
- Arguments: $ARGUMENTS

## Your task

Process a HITL review for an application awaiting RM approval.

Parse `$ARGUMENTS`:
- First token = `application_id`
- Second token = `approve` or `reject`
- Remaining tokens = rejection reason (only for `reject`)

### If no arguments — show the queue

Display the full HITL queue in a formatted table:
```
Application ID | Applicant | Loan Amount | Risk Summary | Waiting Since
```
Ask the user which application to review and whether to approve or reject.

### If `approve`

1. Fetch the HITL review details to show context:
   ```
   curl -s http://localhost:8000/rm/queue | python3 -m json.tool
   ```

2. Show the AI risk summary and recommended decision for this application.

3. Ask for confirmation: "Approve application `<id>` for ₹`<amount>`? (yes/no)"

4. On confirmation, POST the approval:
   ```
   curl -s -X POST http://localhost:8000/rm/approve/<application_id> \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer <token>" \
     -d '{"reviewer_notes": "Approved via RM dashboard"}' | python3 -m json.tool
   ```

5. Confirm that the `hitl.approved` event was published to Redis Streams:
   ```
   docker compose exec redis redis-cli XLEN hitl.approved
   ```

6. Watch for the pipeline to resume (poll `/status/<application_id>` 3 times, 5 seconds apart).

### If `reject`

1. Require a rejection reason — if not provided, ask for one.

2. Ask for confirmation: "Reject application `<id>` with reason: `<reason>`? (yes/no)"

3. On confirmation, POST the rejection:
   ```
   curl -s -X POST http://localhost:8000/rm/reject/<application_id> \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer <token>" \
     -d '{"rejection_reason": "<reason>", "reviewer_notes": "Rejected via RM dashboard"}' | python3 -m json.tool
   ```

4. Confirm that `hitl.rejected` event was published and the pipeline moved to a rejected state.

### Notes
- Never approve without showing the risk summary first.
- Always require a reason for rejection.
- If the application is not in HITL state, report the current state and stop.
