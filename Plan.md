# Loan Disbursement System — Remaining Plan

## Phase 1 — Complete Agent Nodes (6 stubs remaining)

All nodes must follow the `lead_capture` / `sanction_processing` pattern: render Jinja2 prompt → call Claude → parse JSON → publish `node.completed` → return updated state.

| Node | State fields to set | Router to wire |
|---|---|---|
| `lead_qualification` | `qualification_result: qualified\|rejected`, `qualification_notes` | `route_after_qualification` — currently always returns `"continue"` |
| `identity_verification` | `identity_verified: bool`, `kyc_status`, `identity_provider_response` | none (linear edge) |
| `credit_assessment` | `credit_score`, `credit_decision: approve\|reject\|manual_review`, `suggested_loan_amount` | none (linear edge) |
| `fraud_detection` | `fraud_risk_score`, `fraud_signals`, `fraud_decision: clear\|flag\|block` | `route_after_fraud` — currently always returns `"continue"` |
| `compliance` | `compliance_checks`, `compliance_decision: pass\|fail`, `compliance_notes` | none (linear edge) |
| `document_collection` | `documents_verified: bool`, `required_documents`, `ocr_results` | none (linear edge) |
| `disbursement` | `disbursement_status: success\|failed`, `disbursement_reference` | none; on failure enqueue `retry_disbursement` Celery task |

**Also wire the two stub routers** once the nodes above produce real output fields:
- `route_after_qualification` → `"continue"` if `qualification_result == "qualified"` else `"reject"`
- `route_after_fraud` → `"block"` if `fraud_decision == "block"` else `"continue"`

**Also implement `retry_disbursement`** Celery task (`agent-service/worker/tasks.py`):
- Retry schedule: immediate → 1 h → 4 h → 24 h (max 4 retries, already configured)
- On permanent failure: set `disbursement_status = "failed"`, publish `pipeline.completed`

---

## Phase 4 — Notification Service

Scaffolded but entirely unwired. All work is in `notification-service/`.

1. `consumers/event_consumer.py` — consume `loan:events` stream (group: `notification-service-group`)
2. `worker/tasks.py` — implement four Celery tasks:
   - `send_stage_notification` — stage update SMS/email to applicant on each `node.completed`
   - `send_rejection_notification` — rejection reason + improvement guidance on `pipeline.completed` with rejected status
   - `send_disbursement_confirmation` — success message + EMI schedule on successful disbursement
   - `send_rm_hitl_alert` — alert RM channel/email when `hitl.requested` fires
3. Wire `twilio_service.py` (SMS/WhatsApp) and `sendgrid_service.py` (email) — both are scaffolded, just need credentials and call sites
4. Deploy `notification-service` + `notification-worker` to Railway
5. Add env vars to Railway: `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_FROM_NUMBER`, `SENDGRID_API_KEY`

---

## Phase 7 — Hardening

| Item | File | What to do |
|---|---|---|
| **Celery Beat** | `docker-compose.yml` + `agent-service/worker/` | Deploy `celery-beat` container; add scheduled tasks: doc reminder at 24h/48h/72h, RM follow-up after 5 days stalled, sanction nudge after 48h |
| **Auth** | `backend-api/middleware/auth.py` | JWT middleware exists but is not enforced. At minimum add auth to all `/rm/*` routes via FastAPI dependency injection |
| **Error handling** | `backend-api/services/event_consumer.py` | On node failure (pipeline error), set `Application.status = "error"` and broadcast WebSocket event; show error state in `WorkflowTimeline` |
| **RAG / pgvector** | `agent-service/agents/compliance/agent.py` | Run `/seed-rag` to populate pgvector with RBI guidelines; wire `policy_rag_tool` to query embeddings and inject relevant policy into the compliance prompt |

---

## Summary

| Phase | Status | Priority |
|---|---|---|
| Phase 1 — Agent nodes (6 remaining) | 🔄 Partial | **High** — core product doesn't work without real node decisions |
| Phase 4 — Notifications | Not started | Medium — user-facing feature |
| Phase 7 — Hardening | Low–Medium | Low–Medium — production readiness |
