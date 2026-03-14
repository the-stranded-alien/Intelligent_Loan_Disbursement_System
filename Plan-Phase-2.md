# Phase 2 — Completion Plan

## Phase 1 — Core Pipeline (Agent Nodes)

The highest value work. Each node follows the same pattern as `lead_capture`.

| Node | What it needs |
|---|---|
| `lead_qualification` | Mock PAN validation + Claude decision → `qualification_result: qualified\|rejected`. Wire `route_after_qualification` router to read this field. |
| `identity_verification` | Mock OCR result + Claude identity check → `identity_verified: bool`, `kyc_status` |
| `credit_assessment` | Mock CIBIL score (random 300–900) + Claude risk decision → `credit_score`, `credit_decision: approve\|reject\|manual_review` |
| `fraud_detection` | Mock fraud signals + Claude analysis → `fraud_risk_score`, `fraud_decision: clear\|flag\|block`. Wire `route_after_fraud` router. |
| `compliance` | Mock AML/PEP check + Claude compliance → `compliance_decision: pass\|fail` |
| `document_collection` | Check `uploaded_documents` in state + Claude orchestration → `documents_verified: bool` |
| `sanction_processing` | Claude generates loan terms → `sanction_amount`, `sanction_terms`. Set `hitl_required = loan_amount > ₹10L`. Wire `route_after_sanction` router. |
| `disbursement` | Mock bank transfer → `disbursement_status: success\|failed`. Implement Celery retry chain on failure. |

---

## Phase 2 — Real-time Pipeline Updates

Currently one `node.completed` event fires at the **end** of the full graph run. For the UI to update live as each node executes, each agent node needs to publish its own `node.completed` event mid-graph. This requires a shared `event_publisher` instance accessible inside each agent node.

---

## Phase 3 — HITL Flow

For loans >₹10L, the pipeline pauses before `sanction_processing`. The full loop:

1. `sanction_processing` sets `hitl_required = True`, publishes `hitl.requested` event
2. RM Dashboard shows the application in the review queue
3. RM clicks Approve/Reject → `POST /api/v1/rm/approve/{id}` or `/rm/reject/{id}`
4. `backend-api` publishes `hitl.decision` event to `loan:hitl:decisions` stream
5. `agent-service` consumer reads it → enqueues `resume_pipeline` Celery task
6. `resume_pipeline` loads checkpoint from Postgres, injects RM decision, resumes graph
7. Graph continues to `disbursement`

> `resume_pipeline` task in `agent-service/worker/tasks.py` is currently a stub.

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

| Phase | Effort | Value |
|---|---|---|
| Phase 1 — Agent nodes | High | Core product |
| Phase 2 — Per-node events | Low | Live UI experience |
| Phase 3 — HITL loop | Medium | Complete workflow |
| Phase 4 — Notifications | Medium | User-facing feature |
| Phase 5 — Analytics | Low | Dashboard value |
| Phase 6 — Frontend polish | Medium | Demo quality |
| Phase 7 — Hardening | Low–Medium | Production readiness |

**Next step:** Phase 1, starting with `lead_qualification` — it has the first real routing decision that affects the pipeline path.
