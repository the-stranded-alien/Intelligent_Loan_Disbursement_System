# Phase 2 — Completion Plan

## ✅ Phase 1 — Core Pipeline (Agent Nodes)

`sanction_processing` is now fully implemented (Claude call + HITL awareness). The remaining 6 stub nodes need the same treatment — each follows the same pattern as `lead_capture`.

| Node | Status | What it still needs |
|---|---|---|
| `lead_qualification` | Stub | Mock PAN validation + Claude decision → `qualification_result: qualified\|rejected`. Wire `route_after_qualification` router to read this field. |
| `identity_verification` | Stub | Mock OCR result + Claude identity check → `identity_verified: bool`, `kyc_status` |
| `credit_assessment` | Stub | Mock CIBIL score (random 300–900) + Claude risk decision → `credit_score`, `credit_decision: approve\|reject\|manual_review` |
| `fraud_detection` | Stub | Mock fraud signals + Claude analysis → `fraud_risk_score`, `fraud_decision: clear\|flag\|block`. Wire `route_after_fraud` router. |
| `compliance` | Stub | Mock AML/PEP check + Claude compliance → `compliance_decision: pass\|fail` |
| `document_collection` | Stub | Check `uploaded_documents` in state + Claude orchestration → `documents_verified: bool` |
| `sanction_processing` | ✅ Done | Claude generates loan terms → `sanction_amount`, `sanction_terms`. `hitl_required` flag set. `route_after_sanction` wired. |
| `disbursement` | Stub | Mock bank transfer → `disbursement_status: success\|failed`. Implement Celery retry chain on failure (`retry_disbursement` task). |

Note: `route_after_qualification` and `route_after_fraud` routers are still stubs (always return `"continue"`). They need to be wired once those nodes produce real output fields.

---

## ✅ Phase 2 — Real-time Pipeline Updates

**Done.** Each of the 9 agent nodes now publishes its own `node.completed` event to `loan:events` as soon as it finishes. The end-of-pipeline event in `run_pipeline` was changed to `pipeline.completed` to avoid collision. The `backend-api` event consumer handles both:

- `node.completed` → updates `app.current_stage` in DB + broadcasts via WebSocket
- `pipeline.completed` → sets `app.status = "completed"` + broadcasts via WebSocket

---

## ✅ Phase 3 — HITL Flow

**Done.** The full loop is wired end-to-end:

1. `run_pipeline` task runs 7 nodes, pauses at `interrupt_before=["sanction_processing"]`
2. If `loan_amount > ₹10L`: publishes `hitl.requested` → `backend-api` sets `app.status = "pending_review"` + WebSocket broadcast → RM sees it in `/api/v1/rm/queue`
3. If `loan_amount ≤ ₹10L`: immediately auto-resumes via second `ainvoke(None)`
4. RM clicks Approve/Reject → `POST /api/v1/rm/{id}/review`
5. `backend-api` saves review to DB + publishes `hitl.decision` to `loan:hitl:decisions` stream
6. `HitlDecisionConsumer` (new, in `agent-service/consumers/hitl_consumer.py`) reads it → enqueues `resume_pipeline` Celery task
7. `resume_pipeline` calls `graph.aupdate_state()` to inject `hitl_decision` into checkpoint, then `ainvoke(None)` to resume
8. `sanction_processing` runs (with `hitl_decision` visible in state), `route_after_sanction` routes to `disbursement` or `END`
9. `pipeline.completed` event fires

---

## Phase 4 — Notification Service

Currently scaffolded but not wired. Needs:

1. Implement `notification-service/consumers/event_consumer.py` — consume `loan:events` stream
2. Implement `notification-service/worker/tasks.py`:
   - `send_stage_notification` — stage update SMS/email to applicant
   - `send_rejection_notification` — rejection with improvement guidance
   - `send_disbursement_confirmation` — success + EMI schedule
   - `send_rm_hitl_alert` — RM alert when review is required
3. Wire `twilio_service.py` (SMS/WhatsApp) and `sendgrid_service.py` (email)
4. Deploy `notification-service` + `notification-worker` to Railway
5. Add `TWILIO_*` and `SENDGRID_API_KEY` to Railway env vars

---

## Phase 5 — Analytics & Dashboard Data

Currently the analytics endpoints return mock/empty data. Needs:

1. `GET /api/v1/analytics/pipeline` — real counts from DB (total, by status, by stage, conversion funnel)
2. `GET /api/v1/analytics/agents` — average processing time per node, rejection rates per node
3. Wire `frontend/src/pages/Analytics.tsx` charts to real API data

---

## Phase 6 — Frontend Polish

| Component | What's needed |
|---|---|
| `StatusTracker.tsx` | `AgentDecisionCard` per node — show actual Claude reasoning from `stage_results` |
| `RMDashboard.tsx` | Verify approve/reject buttons call the API correctly |
| `WhatIfAnalysis.tsx` | Loan amount slider → re-run risk assessment with different amount |
| `NotificationFeed.tsx` | Show recent SMS/email events per application |
| WebSocket | Verify live stage updates work on status tracker as nodes complete |

---

## Phase 7 — Hardening

| Item | Details |
|---|---|
| **Celery Beat** | Deploy `celery-beat` to Railway for scheduled tasks — doc reminders at 24h/48h/72h, RM follow-ups after 5 days stalled, sanction nudge after 48h |
| **Auth** | JWT middleware exists at `backend-api/middleware/auth.py` but is not enforced on any routes. Add auth to RM routes at minimum. |
| **Error handling** | When a node fails, update `Application.status = "error"` in DB and broadcast via WebSocket |
| **RAG / pgvector** | `compliance` node is designed to use RAG over RBI guidelines. Run `/seed-rag` to populate pgvector, wire `policy_rag_tool` in compliance agent. |

---

## Summary

| Phase | Status | Effort | Value |
|---|---|---|---|
| Phase 1 — Agent nodes | 🔄 Partial (1/8 nodes done) | High | Core product |
| Phase 2 — Per-node events | ✅ Done | Low | Live UI experience |
| Phase 3 — HITL loop | ✅ Done | Medium | Complete workflow |
| Phase 4 — Notifications | Not started | Medium | User-facing feature |
| Phase 5 — Analytics | Not started | Low | Dashboard value |
| Phase 6 — Frontend polish | Not started | Medium | Demo quality |
| Phase 7 — Hardening | Not started | Low–Medium | Production readiness |

**Next step:** Phase 1 — implement the remaining 6 stub agent nodes, starting with `lead_qualification` (it has the first real routing decision that affects the pipeline path).
