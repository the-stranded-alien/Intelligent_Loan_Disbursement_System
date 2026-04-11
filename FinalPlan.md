# Final Plan — Intelligent Loan Disbursement System

## Status as of 2026-04-11

All planned features are **complete**. The system is a fully working end-to-end
intelligent loan disbursement platform. This document tracks what was built across
the two implementation sessions.

---

## ✅ Completed Work

### Part 1 — Pipeline Node Refinements

| Item | Status | Notes |
|------|--------|-------|
| Min loan ₹10k → ₹1k | ✅ Done | `loanSchema.min(1000)` in ApplicationForm.tsx |
| Expand form fields (city, state, residential, employer) | ✅ Done | Step 1 + Step 2 in ApplicationForm.tsx |
| Alembic migration 0006 | ✅ Done | Adds 6 lead gen columns to applications table |
| Lead capture prompt updated | ✅ Done | Rules 9/10 for residential/employment stability |
| ApplicationState extended | ✅ Done | 6 new fields in graph/state.py |
| Eligibility banner on StatusTracker | ✅ Done | Green/red banner from lead_capture audit event |
| Eligibility email on eligible result | ✅ Done | Fires via notification-service on node.completed |
| ApplicationForm eligibility polling screen | ✅ Done | Polls /events, shows checking → eligible/ineligible |
| Node 2 `request_info` path | ✅ Done | Router handles it (treated as reject, stub noted) |
| Node 4 mock CIBIL tool_use | ✅ Done | SHA-256 PAN hash → deterministic score bands |
| Differentiated credit scoring | ✅ Done | Grade A/B/C/D → different rates per applicant |
| ART offers card on StatusTracker | ✅ Done | 3-column card from art_negotiation audit event |
| HITL threshold lowered to ₹2L | ✅ Done | `hitl_threshold: int = 200_000` |
| node.started / node.completed events | ✅ Done | All 7 nodes publish both events |
| activeStage live UI indicator | ✅ Done | Wired in StatusTracker → WorkflowTimeline |
| Decimal → percent conversion | ✅ Done | face_match_confidence, dti_ratio, affordability_ratio |
| WebSocket reconnect loop fix | ✅ Done | `dead` ref pattern in useWorkflowSocket |

### Part 2 — Background Agents

| Agent | Status | Notes |
|-------|--------|-------|
| **Monitoring Agent** | ✅ Done | Hourly Celery Beat scan, STALE_THRESHOLDS per status |
| **Outreach Agent** | ✅ Done | LLM-generated messages, 4-attempt cap, email + SMS |
| **Assessment Agent** | ✅ Done | Multi-turn chat (AssessmentSession), WS endpoint |
| **Negotiation Agent** | ✅ Done | Offer recommendation + risk analysis for RM |

### Part 3 — Frontend

| Item | Status | Notes |
|------|--------|-------|
| ApplicationForm eligibility result screen | ✅ Done | Polls for lead_capture result, shows pass/fail inline |
| StatusTracker eligibility banner | ✅ Done | Green (eligible) / red (ineligible) with reason |
| StatusTracker ART offers card | ✅ Done | 3 options A/B/C with recommended badge |
| StatusTracker "Start Assessment" button | ✅ Done | Shown when status = pending_review |
| AssessmentChat page | ✅ Done | `/assessment/:applicationId`, WS chat, result card |
| RMDashboard "Start Assessment" button | ✅ Done | Navigates to AssessmentChat |
| NegotiationPanel component | ✅ Done | Auto-loads advice when RM selects an application |
| ApplicationsList status fixes | ✅ Done | completed, pending_review statuses + display |
| Analytics PIPELINE_STAGES fix | ✅ Done | Updated to 7-node list |
| STAGE_LABELS fixes across pages | ✅ Done | Removed old 9-node stages |

### Part 4 — Infrastructure & Notifications

| Item | Status | Notes |
|------|--------|-------|
| SendGrid send_email implemented | ✅ Done | Real API call, graceful no-op if key missing |
| Twilio send_sms / send_whatsapp implemented | ✅ Done | Lazy-init client |
| notify_outreach Celery task | ✅ Done | Email + SMS dispatch |
| All notification stubs filled | ✅ Done | received, approved, rejected, document_reminder, disbursement |
| notification-service /internal/send-outreach | ✅ Done | HTTP endpoint for agent-service to call |
| eligibility email on lead_capture pass | ✅ Done | Fired from backend-api event_consumer |
| LangSmith tracing | ✅ Done | configure_tracing() at startup, env vars in docker-compose |
| langsmith added to requirements | ✅ Done | `langsmith==0.2.3` |
| AGENT_SERVICE_URL in frontend nginx | ✅ Done | /api/v1/assessment/ proxied to agent-service |
| docker-compose frontend AGENT_SERVICE_URL | ✅ Done | Points to loan-agent-service:8001 |

### Part 5 — Metrics, Retry & RM Tools (Session 3)

| Item | Status | Notes |
|------|--------|-------|
| `call_llm` utility — token + latency metrics | ✅ Done | `agent-service/services/llm_utils.py`; wraps all LLM calls |
| Per-node metrics in stage_results | ✅ Done | `**metrics` in all 7 agents (enach, esign, lead_capture, lead_qualification, identity_verification, credit_assessment, art_negotiation) |
| Node 2 `request_info` real status path | ✅ Done | event_consumer sets `status=info_requested` on WS + DB when qualification_result==request_info |
| `info_requested` status in frontend | ✅ Done | STATUS_COLORS entry + WS event handler in StatusTracker |
| Disbursement retry logic | ✅ Done | `retry_disbursement` Celery task: simulated bank API, exponential back-off (0→1h→4h→24h), publishes disbursed event on success |
| Counter-offer simulator — backend | ✅ Done | `POST /api/v1/rm/{id}/counter-offer` in rm.py; pure EMI math, reads sanctioned amount from audit log |
| Counter-offer simulator — frontend | ✅ Done | Rate + tenure inputs in NegotiationPanel; shows EMI, total payable, interest cost |
| Document upload UI | ✅ Done | Upload card in StatusTracker (shown when info_requested or processing); calls `POST /api/v1/documents/{id}/upload` |

---

## System Architecture (Final)

```
┌─────────────────────────────────────────────────────────────────┐
│  Frontend (React 18 + shadcn/ui) — port 3000                    │
│  Pages: Apply, Track, RM Dashboard, Applications, Analytics      │
│  + AssessmentChat (/assessment/:id)                              │
└──────────────┬──────────────────────────────┬───────────────────┘
               │ /api/*                        │ /api/v1/assessment/*
               ▼                              ▼
┌─────────────────────────┐   ┌────────────────────────────────────┐
│  backend-api (port 8000) │   │  agent-service (port 8001)         │
│  FastAPI + SQLAlchemy    │   │  FastAPI + LangGraph               │
│  Event consumer (Redis)  │   │  Assessment WS endpoint            │
│  WebSocket manager       │   │  Negotiation HTTP endpoint         │
│  RM + analytics routers  │   │  Celery worker (agent queue)       │
└──────────┬──────────────┘   │  Celery Beat (hourly monitoring)   │
           │                  └──────────────┬─────────────────────┘
           │ Redis Streams (loan:events)      │
           └──────────────────┬──────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  LangGraph 7-node pipeline                                       │
│  lead_capture → lead_qualification → identity_verification       │
│  → credit_assessment (mock CIBIL tool_use)                       │
│  → art_negotiation (HITL interrupt > ₹2L)                       │
│  → enach → esign                                                 │
└─────────────────────────────────────────────────────────────────┘
           │
           ▼
┌──────────────────────────────────┐
│  notification-service (port 8002) │
│  Celery worker (notifications)    │
│  SendGrid + Twilio                │
│  /internal/send-outreach endpoint │
└──────────────────────────────────┘
```

### Background Agents (outside LangGraph)

```
Celery Beat (hourly)
  └─→ monitoring_scan task
        ├─→ publishes outreach.required to Redis Streams
        └─→ enqueues run_outreach Celery task
              └─→ Claude generates personalised message
                    └─→ POST /internal/send-outreach
                          └─→ notify_outreach task → SendGrid + Twilio
                    └─→ writes outreach.sent to audit_log

RM opens pending_review application
  └─→ GET /api/v1/rm/{id}/negotiation-advice
        └─→ agent-service POST /api/v1/negotiation/analyse
              └─→ Claude analyses 3 offers → recommendation JSON

RM clicks "Start Assessment"
  └─→ POST /api/v1/assessment/{id}/start → session_id
        └─→ WS /api/v1/assessment/ws/{session_id}
              └─→ AssessmentSession (Claude multi-turn)
                    └─→ POST /{session_id}/finalize → result JSON
```

---

## File Map (All New Files Created)

```
agent-service/
├── agents/
│   ├── monitoring/
│   │   ├── __init__.py
│   │   └── agent.py              ✅ run_monitoring_scan()
│   ├── outreach/
│   │   ├── __init__.py
│   │   └── agent.py              ✅ run_outreach(payload)
│   ├── assessment/
│   │   ├── __init__.py
│   │   └── agent.py              ✅ AssessmentSession class
│   └── negotiation/
│       ├── __init__.py
│       └── agent.py              ✅ run_negotiation_analysis()
├── routers/
│   ├── __init__.py
│   ├── assessment.py             ✅ REST + WS endpoints
│   └── negotiation.py            ✅ POST /analyse
├── db/
│   └── session.py                ✅ Read-only SQLAlchemy mirror
├── config/prompts/
│   ├── outreach.j2               ✅ Personalised follow-up prompt
│   ├── assessment.j2             ✅ "Priya" advisor persona
│   └── negotiation.j2            ✅ Offer analysis prompt
└── services/
    └── tracing.py                ✅ LangSmith configure_tracing()

backend-api/
└── db/migrations/versions/
    └── 0006_add_lead_gen_fields.py  ✅

frontend/src/
├── pages/
│   └── AssessmentChat.tsx        ✅ Chat UI + result card
└── components/
    └── NegotiationPanel.tsx      ✅ Offer recommendation panel
```

---

### Part 6 — Assessment Auto-trigger from Node 2

| Item | Status | Notes |
|------|--------|-------|
| Auto-start AssessmentSession on `request_info` | ✅ Done | event_consumer calls agent-service `POST /api/v1/assessment/{id}/start` fire-and-forget |
| `GET /session/{session_id}` endpoint | ✅ Done | Returns metadata for pre-created sessions (no re-POST needed) |
| `assessment_ready` WS broadcast | ✅ Done | Includes `session_id` + `opening` after session is created |
| StatusTracker assessment banner | ✅ Done | Violet banner with "Start Chat" → `/assessment/{id}?session={sid}` |
| AssessmentChat `?session=` param | ✅ Done | Resumes pre-created session instead of starting a new one |
| `PipelineEvent` type fields added | ✅ Done | `session_id`, `opening`, `reason` added to interface |

## Remaining Opportunities (Post-MVP)

These items are optional and not blocking:

| Item | Notes |
|------|-------|
| Auth0 integration | Planned in Phase 5; all endpoints currently open |
| pgvector RAG seeding | compliance_policies collection; `/seed-rag` skill available |
| Real bank disbursement API | Replace random simulation in `retry_disbursement` with IMPS/NEFT call |
