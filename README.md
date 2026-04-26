# Intelligent Loan Disbursement System

> **Live deployment:** [https://loan-agent.guptasahil.in](https://loan-agent.guptasahil.in)

An agentic AI system for fully automated loan processing — from lead capture through to bank disbursement — powered by **LangGraph 0.2**, **FastAPI**, and **Claude claude-sonnet-4-6**.

---

## Table of Contents

1. [Overview](#1-overview)
2. [System Architecture](#2-system-architecture)
3. [LangGraph Pipeline](#3-langgraph-pipeline)
4. [Human-in-the-Loop Gates](#4-human-in-the-loop-gates)
5. [Background Agents](#5-background-agents)
6. [Agent Reasoning Traces](#6-agent-reasoning-traces)
7. [Frontend Pages](#7-frontend-pages)
8. [Services & Ports](#8-services--ports)
9. [Tech Stack](#9-tech-stack)
10. [Data Flow](#10-data-flow)
11. [Database Schema](#11-database-schema)
12. [Event Bus (Redis Streams)](#12-event-bus-redis-streams)
13. [Railway Deployment](#13-railway-deployment)
14. [Local Development](#14-local-development)
15. [Environment Variables](#15-environment-variables)
16. [API Reference](#16-api-reference)
17. [Database Migrations](#17-database-migrations)

---

## 1. Overview

The system processes loan applications through a **7-node LangGraph pipeline**. Each node is a Claude-powered agent that reads application state, calls the Anthropic API with a Jinja2-rendered prompt, parses the JSON response, and writes structured output back to the shared `ApplicationState`.

Two mandatory human/user gates interrupt the pipeline before it can proceed:

1. **Repayment Assessment** (before KYC) — an AI-led multi-turn chat with the applicant
2. **KYC Document Upload** (before identity verification) — applicant must upload PAN/Aadhaar
3. **RM HITL** (before ART negotiation, loans > ₹2 L) — relationship manager approval

A pair of background agents run continuously:

- **Monitoring Agent** — scans for stale applications every 2 minutes and flags them
- **Outreach Agent** — generates personalised follow-up messages via Claude and dispatches them through the notification service

---

## 2. System Architecture

```
  Browser (React 18 + TypeScript + Vite)
    │  HTTPS → nginx reverse proxy
    │
    ▼
  ┌─────────────────────────────────────────────────────────────────┐
  │                         nginx (frontend)                         │
  │  /          → React SPA                                         │
  │  /api/       → backend-api (proxy)                              │
  │  /ws/        → backend-api WebSocket (proxy, Upgrade headers)   │
  │  /health     → backend-api /health (proxy)                      │
  └──────────────────────────┬──────────────────────────────────────┘
                             │ HTTP / WebSocket
                             ▼
  ┌─────────────────────────────────────────────────────────────────┐
  │                      backend-api  :8000                          │
  │  FastAPI + SQLAlchemy + psycopg2                                 │
  │                                                                  │
  │  Routers:                                                        │
  │    POST /api/v1/applications/          — submit application      │
  │    GET  /api/v1/applications/{id}      — full application data   │
  │    GET  /api/v1/applications/{id}/status                         │
  │    GET  /api/v1/applications/{id}/events   — audit log           │
  │    GET  /api/v1/applications/{id}/traces   — agent traces        │
  │    POST /api/v1/documents/{id}/upload  — KYC doc upload          │
  │    GET  /api/v1/rm/queue               — RM review queue         │
  │    POST /api/v1/rm/{id}/decision       — RM approve/reject       │
  │    POST /api/v1/assessment/{id}/start  — start repayment chat    │
  │    WS   /api/v1/assessment/ws/{sid}    — assessment WebSocket    │
  │    POST /api/v1/assessment/{sid}/finalize                        │
  │    GET  /api/v1/analytics/evaluation   — agent trace metrics     │
  │    GET  /api/v1/analytics/background-agents                      │
  │    POST /api/v1/analytics/trigger-monitoring                     │
  │    WS   /ws/{application_id}           — live pipeline events    │
  │                                                                  │
  │  Services:                                                       │
  │    EventConsumer   — reads loan:events Redis Stream              │
  │    WebSocketManager — broadcasts to connected browser clients    │
  └──────┬──────────────────────────────────────────────────────────┘
         │
         ├── PostgreSQL 16 (shared DB)
         │     applications, audit_logs, documents, rm_reviews,
         │     agent_traces, alembic_version
         │
         ├── Redis DB0 (loan:events stream, loan:applications stream,
         │             loan:hitl:decisions stream)
         │
         └── Redis DB1 (Celery broker — send_task to agent queue)

  ┌─────────────────────────────────────────────────────────────────┐
  │                    agent-service  :8001                          │
  │  FastAPI + LangGraph + psycopg3                                  │
  │                                                                  │
  │  Consumers (asyncio tasks in lifespan):                          │
  │    AgentEventConsumer  — reads loan:applications stream          │
  │                          → enqueues agent.run_pipeline           │
  │    HitlDecisionConsumer — reads loan:hitl:decisions stream       │
  │                          → enqueues agent.resume_pipeline        │
  └──────┬──────────────────────────────────────────────────────────┘
         │
         ├── agent-worker (Celery, SERVICE=worker)
         │     Executes: run_pipeline, resume_pipeline,
         │               run_outreach, monitoring_scan
         │
         └── agent-beat  (Celery Beat, SERVICE=beat)
               Schedules: monitoring_scan every 2 minutes
```

---

## 3. LangGraph Pipeline

The pipeline is compiled as a `StateGraph[ApplicationState]` with `AsyncPostgresSaver` as the checkpointer. Every node completion is persisted to PostgreSQL so the pipeline survives restarts.

```
  application.created event
        │
        ▼
  ┌─────────────┐     ineligible
  │ lead_capture │ ──────────────────────→ END (rejected)
  │  (critic)    │
  └──────┬───────┘
         │ eligible
         ▼
  ┌──────────────────┐    hard fail
  │ lead_qualification│ ──────────────────→ END (rejected)
  │    (analyst)      │
  └──────┬────────────┘
         │ pass / request_info
         │
         │   ← interrupt_before ──────────────────────────┐
         ▼                                                  │
  ┌──────────────────┐   GATE 1: Repayment Assessment       │
  │  [PAUSED]        │   Backend sets status=info_requested  │
  │  assessment chat │   Auto-starts AssessmentSession       │
  │  (multi-turn     │   Applicant chats with "Priya" (AI)   │
  │   Claude conv.)  │   On approve → status=kyc_pending     │
  └──────┬───────────┘                                       │
         │ assessment approved                               │
         ▼                                                   │
  ┌──────────────────┐   GATE 2: KYC Document Upload         │
  │  [PAUSED]        │   Applicant uploads PAN/Aadhaar        │
  │  kyc_pending     │   Upload triggers hitl.decision event  │
  └──────┬───────────┘   resume_pipeline enqueued            │
         │ doc uploaded                                      │
         ▼                                                   │
  ┌──────────────────┐   failed / mismatch                   │
  │identity_verify   │ ──────────────────────────────────────→ END
  │   (critic)       │
  └──────┬───────────┘
         │ verified
         ▼
  ┌──────────────────┐    reject
  │ credit_assessment│ ──────────────────→ END (rejected)
  │    (analyst)     │
  │  2-turn tool-use │
  │  CIBIL lookup    │
  └──────┬───────────┘
         │ approve
         │
         │   ← interrupt_before (loans > ₹2L only) ─────────┐
         ▼                                                    │
  ┌──────────────────┐   GATE 3: RM HITL (large loans)        │
  │  art_negotiation │   RM reviews in dashboard              │
  │    (planner)     │   Approve / reject decision            │
  │  3 loan offers   │   resume_pipeline called after         │
  └──────┬───────────┘                                        │
         │ approved (small loans auto-resume)                 │
         ▼
  ┌──────────────────┐
  │     enach        │  e-NACH mandate simulation
  │  (coordinator)   │
  └──────┬───────────┘
         │
         ▼
  ┌──────────────────┐
  │     esign        │  Aadhaar OTP e-sign simulation
  │  (coordinator)   │
  └──────┬───────────┘
         │
         ▼
  pipeline.completed event → status=completed
```

### Node Details

| Node | Role | Model | Key Output Fields |
|---|---|---|---|
| `lead_capture` | critic | claude-sonnet-4-6 | `eligibility_result`, `eligibility_reason`, `data_quality_issues` |
| `lead_qualification` | analyst | claude-sonnet-4-6 | `qualification_result`, `verified_income`, `max_eligible_amount`, `affordability_ratio` |
| `identity_verification` | critic | claude-sonnet-4-6 | `identity_verified`, `pan_verified`, `name_match`, `kyc_status`, `face_match_confidence` |
| `credit_assessment` | analyst | claude-sonnet-4-6 | `credit_score`, `credit_decision`, `repayment_history` (2-turn tool-use) |
| `art_negotiation` | planner | claude-sonnet-4-6 | `negotiation_offers[]`, `sanctioned_amount`, `interest_rate_percent`, `monthly_emi` |
| `enach` | coordinator | claude-sonnet-4-6 | `enach_status`, `enach_reference`, `mandate_id` |
| `esign` | coordinator | claude-sonnet-4-6 | `esign_status`, `esign_reference`, `agreement_url`, `signed_at` |

### ART Negotiation — Python-computed EMI

The ART agent asks Claude only for rates and tenures. All financial fields are recomputed in Python after parsing to eliminate LLM arithmetic errors:

```python
def _emi(principal, annual_rate_pct, tenure_months):
    r = annual_rate_pct / 12 / 100
    return round(principal * r * (1+r)**tenure_months / ((1+r)**tenure_months - 1), 2)
```

### Prompt System

Every agent renders its prompt from a Jinja2 template in `agent-service/config/prompts/<node>.j2`. Prompts instruct Claude to respond with a single JSON object. The `parse_llm_json` utility extracts JSON from fenced code blocks or bare objects.

---

## 4. Human-in-the-Loop Gates

### Gate 1 — Repayment Assessment Chat

**Trigger:** Pipeline runs nodes 1–2 (lead_capture + lead_qualification), then always pauses before `identity_verification` and publishes `assessment_required` to `loan:events`.

**Backend flow:**
1. `event_consumer` receives `assessment_required` → sets `app.status = info_requested`
2. Auto-creates an `AssessmentSession` in memory → broadcasts `assessment_ready` WS event with session ID
3. Applicant navigates to `/assessment/{id}?session={sid}` and chats with "Priya" over WebSocket
4. Claude asks 5 structured questions (income stability, upcoming expenses, backup plan, EMI management, loan purpose)
5. After all 5 questions, Claude outputs a JSON assessment block: `repayment_confidence`, `recommendation`, `risk_flags`, `assessment_notes`
6. `is_complete: true` triggers `POST /api/v1/assessment/{sid}/finalize`
7. `finalize_assessment` saves to `audit_logs` and sets `app.status = kyc_pending`

### Gate 2 — KYC Document Upload

**Trigger:** `finalize_assessment` sets `app.status = kyc_pending` and broadcasts `kyc_required` WS event.

**UI:** StatusTracker shows an orange "Action Required" card with a file upload form.

**Backend flow:**
1. Applicant uploads any document (PAN card, Aadhaar, etc.) via `POST /api/v1/documents/{id}/upload`
2. `upload_document` detects `app.status == kyc_pending` → sets `app.status = processing` → publishes `hitl.decision` to `loan:hitl:decisions`
3. `HitlDecisionConsumer` in agent-service receives → enqueues `resume_pipeline`
4. `resume_pipeline` checks `snapshot.next = ["identity_verification"]` → resumes graph → identity_verification runs → credit_assessment runs → pauses at art_negotiation

### Gate 3 — RM HITL (loans > ₹2L)

**Trigger:** After credit_assessment approves and loan amount exceeds `HITL_THRESHOLD` (₹2,00,000), `resume_pipeline` publishes `hitl.requested` → sets `app.status = pending_review`.

**UI:** RM Dashboard (`/rm`) shows a queue of pending applications with full audit trail and trace viewer.

**Backend flow:**
1. RM reviews application data, agent traces, and assessment notes
2. `POST /api/v1/rm/{id}/decision` with `approve` or `reject`
3. Decision published to `loan:hitl:decisions` → `resume_pipeline` injects `hitl_decision` into graph state → `route_after_art` routes to `enach` or `END`

---

## 5. Background Agents

### Monitoring Agent

Runs as a scheduled Celery task (`agent.monitoring_scan`) every 2 minutes via Celery Beat.

Scans all open applications by status. Staleness thresholds (demo values):

| Status | Threshold | Meaning |
|---|---|---|
| `pending` | 3 min | Submitted but pipeline never started |
| `processing` | 3 min | Pipeline stuck mid-run |
| `pending_review` | 3 min | RM hasn't acted on HITL request |
| `info_requested` | 3 min | Applicant hasn't started assessment chat |
| `kyc_pending` | 3 min | Assessment done but no KYC docs uploaded |

For each stale application (up to 4 attempts):
1. Publishes `outreach.required` to `loan:events` stream
2. Enqueues `agent.run_outreach` Celery task directly

### Outreach Agent

An async Claude-powered function that generates personalised follow-up messages.

**Input:** application ID, full name, loan amount, purpose, status, stage, hours stale, attempt number

**Process:**
1. Renders `outreach.j2` Jinja2 template (context-aware by status — different copy for each stage)
2. Calls `claude-sonnet-4-6` → parses JSON: `subject`, `email_body`, `sms_text`, `urgency`, `suggested_followup_days`
3. POSTs to notification-service `/internal/send-outreach` (Twilio SMS + SendGrid email)
4. Writes `outreach.sent` to `audit_logs` table
5. Publishes `outreach.sent` to `loan:events` for WS broadcast

**Manual trigger:** `POST /api/v1/analytics/trigger-monitoring` enqueues the scan task directly via `celery.send_task` — useful when Celery Beat is not yet deployed.

---

## 6. Agent Reasoning Traces

Every agent node writes one row to `agent_traces` after each LLM call:

| Column | Content |
|---|---|
| `node_name` | e.g. `lead_capture`, `credit_assessment` |
| `agent_role` | `critic` / `analyst` / `planner` / `coordinator` |
| `prompt_rendered` | Full Jinja2-rendered prompt sent to Claude |
| `raw_llm_response` | Exact text returned by Claude |
| `parsed_output` | JSON-parsed result dict |
| `duration_ms` | LLM call wall-clock time |
| `input_tokens` / `output_tokens` | Token usage from response metadata |
| `model` | Model ID used (`claude-sonnet-4-6`) |

Traces are viewable per-application in the **Evaluation Dashboard** (`/eval`) — Reasoning Trace Explorer section. The per-node token usage chart and call count / latency table aggregate across all applications.

---

## 7. Frontend Pages

| Route | Page | Description |
|---|---|---|
| `/` | Application Form | Multi-field loan application form with validation |
| `/status/:id` | Status Tracker | Real-time pipeline progress via WebSocket; assessment chat banner; KYC upload card; ART offer cards |
| `/rm` | RM Dashboard | HITL review queue; approve/reject with notes; application detail + trace viewer |
| `/applications` | Applications List | Paginated list with status/search filters |
| `/analytics` | Analytics | Overview stats, pipeline funnel, stage breakdown |
| `/assessment/:id` | Assessment Chat | Multi-turn WebSocket chat with "Priya" (repayment assessment AI) |
| `/agents` | Background Agents | Live monitoring + outreach activity feed; manual "Run Scan" trigger |
| `/eval` | Evaluation Dashboard | Agent inventory table with call counts / latency; per-node token usage chart; reasoning trace explorer |

### WebSocket Protocol

All live updates flow over a single WebSocket per application at `WS /ws/{application_id}`. Event types:

| Event | Trigger | Payload |
|---|---|---|
| `node.started` | Agent node begins | `stage` |
| `node.completed` | Agent node finishes | `stage`, `data` |
| `assessment_required` | Pipeline paused for assessment | `stage` |
| `assessment_ready` | Session created | `session_id`, `opening` |
| `assessment.completed` | Chat finalized | `recommendation`, `new_status` |
| `kyc_required` | Assessment approved, docs needed | `message` |
| `kyc_docs_submitted` | Document uploaded | `document_type`, `message` |
| `hitl.requested` | Large loan paused for RM | `loan_amount` |
| `pipeline.completed` | Pipeline finished | `stage`, `status` |
| `outreach.sent` | Follow-up dispatched | `attempt`, `urgency`, `subject` |
| `info_requested` | Qualification needs more info | `reason` |

---

## 8. Services & Ports

| Service | Port | Role |
|---|---|---|
| Frontend (nginx) | 3000 | React SPA + nginx reverse proxy |
| Backend API | 8000 | REST API, WebSocket hub, event consumer |
| Agent Service | 8001 | LangGraph pipeline FastAPI + event consumers |
| Agent Worker | — | Celery worker (`SERVICE=worker`) — executes graph tasks |
| Agent Beat | — | Celery Beat (`SERVICE=beat`) — schedules monitoring scan |
| Notification Service | 8002 | Email (SendGrid) + SMS (Twilio) dispatcher |
| PostgreSQL 16 | 5432 | Primary database |
| Redis 7 | 6379 | DB0: event streams · DB1: Celery broker · DB2: cache |

---

## 9. Tech Stack

### Backend

| Layer | Technology | Version |
|---|---|---|
| AI Orchestration | LangGraph | 0.2.73 |
| LLM | Anthropic Claude | claude-sonnet-4-6 |
| Anthropic SDK | anthropic | 0.45.0 |
| API Framework | FastAPI | 0.115.6 |
| ASGI Server | Uvicorn | 0.34.0 |
| ORM | SQLAlchemy | 2.0.36 |
| DB Adapter (backend-api) | psycopg2-binary | 2.9.10 |
| DB Adapter (agent-service) | psycopg3 (psycopg[binary]) | ≥ 3.0.0 |
| LangGraph Checkpointer | langgraph-checkpoint-postgres | latest |
| Migrations | Alembic | 1.14.0 |
| Task Queue | Celery | 5.3–5.4 |
| Message Broker | Redis | 5.2.1 |
| Prompt Templating | Jinja2 | 3.1.5 |
| HTTP Client | httpx | 0.28.1 |
| Config | pydantic-settings | 2.7.0 |
| Vector Store | pgvector | 0.3.6 |
| LangSmith Tracing | langsmith | 0.2.3 |

### Frontend

| Technology | Version |
|---|---|
| React | 18.3.1 |
| TypeScript | 5.7.2 |
| Vite | 6.0.7 |
| React Router | 6.28.0 |
| Tailwind CSS | 3.4.17 |
| shadcn/ui (Radix) | — |
| Zustand | 5.0.2 |
| Recharts | 2.14.1 |
| Lucide React | 0.469.0 |
| React Hook Form + Zod | 7.54 / 3.24 |

---

## 10. Data Flow

### Application Submission → Pipeline Start

```
Browser POST /api/v1/applications/
  → backend-api creates Application row (status=pending)
  → publishes application.created to loan:applications Redis Stream
  → agent-service AgentEventConsumer receives it
  → enqueues agent.run_pipeline Celery task
  → Celery worker executes run_pipeline
  → asyncio.run(_run()) creates event loop
  → graph.ainvoke(initial_state) runs nodes 1–2
  → pauses at identity_verification interrupt
  → publishes assessment_required to loan:events
  → backend-api EventConsumer receives → sets info_requested
  → auto-starts AssessmentSession → broadcasts assessment_ready WS
```

### Assessment → KYC → Pipeline Resume

```
Applicant clicks "Start Chat" → navigates to /assessment/{id}
  → opens WS /api/v1/assessment/ws/{session_id}
  → exchanges 5 question/answer turns with Claude
  → Claude outputs assessment JSON (is_complete=true)
  → frontend calls POST /api/v1/assessment/{sid}/finalize
  → finalize saves audit log → sets app.status=kyc_pending
  → broadcasts assessment.completed + kyc_required WS events
  → StatusTracker shows KYC upload card

Applicant uploads document → POST /api/v1/documents/{id}/upload
  → upload_document detects kyc_pending
  → sets app.status=processing, publishes hitl.decision
  → HitlDecisionConsumer enqueues resume_pipeline
  → resume_pipeline checks snapshot.next=["identity_verification"]
  → graph.ainvoke(None) runs identity_verification → credit_assessment
  → pauses at art_negotiation
  → small loan: auto-resumes → enach → esign → pipeline.completed
  → large loan: publishes hitl.requested → RM notified
```

### Monitoring → Outreach

```
Celery Beat → enqueues agent.monitoring_scan every 2 min
  → run_monitoring_scan() queries DB for stale apps by status
  → for each stale app (< MAX_OUTREACH_ATTEMPTS=4):
      → publishes outreach.required to loan:events
      → enqueues agent.run_outreach
  → backend-api EventConsumer writes outreach.triggered to audit_logs
  → run_outreach renders outreach.j2 → calls Claude → parses JSON
  → POSTs to notification-service → Twilio SMS + SendGrid email
  → writes outreach.sent to audit_logs (via agent-service DB session)
  → publishes outreach.sent to loan:events
  → backend-api broadcasts outreach.sent WS event to connected clients
```

---

## 11. Database Schema

```sql
-- Core application record
applications (id, full_name, phone, email, pan_number, date_of_birth,
  city, state, residential_status, years_at_current_address,
  employment_type, employer_name, years_in_current_job,
  monthly_income, existing_emi_amount, bank_account_number, ifsc_code,
  loan_amount, loan_purpose, tenure_months,
  status, current_stage, created_at, updated_at)

-- Status values: pending | processing | info_requested | kyc_pending |
--                pending_review | approved | rejected | completed | disbursed

-- Immutable event log (source of truth for UI timeline)
audit_logs (id, application_id, event_type, actor, payload, created_at)

-- KYC and other uploaded files
documents (id, application_id, document_type, storage_path,
  ocr_result, verification_status, created_at)

-- RM review records
rm_reviews (id, application_id, rm_id, decision, notes, conditions, reviewed_at)

-- Per-LLM-call agent reasoning traces (migration 0007)
agent_traces (id, application_id, agent_role, node_name,
  prompt_rendered, raw_llm_response, parsed_output,
  duration_ms, model, input_tokens, output_tokens, created_at)
```

---

## 12. Event Bus (Redis Streams)

Three Redis Streams carry all inter-service communication:

| Stream | Publisher | Consumer | Events |
|---|---|---|---|
| `loan:applications` | backend-api | agent-service AgentEventConsumer | `application.created` |
| `loan:events` | agent-service workers, backend-api | backend-api EventConsumer | `node.started`, `node.completed`, `assessment_required`, `hitl.requested`, `pipeline.completed`, `outreach.required`, `outreach.sent` |
| `loan:hitl:decisions` | backend-api assessment/documents/rm routers | agent-service HitlDecisionConsumer | `hitl.decision` |

Consumer groups ensure at-least-once delivery with `XACK`.

---

## 13. Railway Deployment

The system is deployed on [Railway](https://railway.app) as six services:

| Railway Service | Source | `SERVICE` env var | Start Command |
|---|---|---|---|
| Frontend | `frontend/` | — | nginx |
| Backend API | `backend-api/` | — | `./start.sh` (alembic + uvicorn) |
| Agent Service | `agent-service/` | (unset) | uvicorn main:app |
| Agent Worker | `agent-service/` | `worker` | celery worker |
| Agent Beat | `agent-service/` | `beat` | celery beat |
| PostgreSQL | Railway managed | — | — |
| Redis | Railway managed | — | — |

The `agent-service/Dockerfile` uses the `SERVICE` environment variable to select the process:

```dockerfile
CMD ["sh", "-c", "\
  if [ \"$SERVICE\" = 'worker' ]; then \
    exec celery -A worker.celery_app worker ...; \
  elif [ \"$SERVICE\" = 'beat' ]; then \
    exec celery -A worker.celery_app beat ...; \
  else \
    exec uvicorn main:app ...; \
  fi"]
```

### psycopg3 URL Fix

The agent-service uses psycopg3 (not psycopg2). SQLAlchemy requires `postgresql+psycopg://` prefix for psycopg3's sync driver. The `db/session.py` normalises any Railway-provided URL:

```python
if _db_url.startswith("postgres://"):
    _db_url = "postgresql+psycopg://" + _db_url[len("postgres://"):]
elif _db_url.startswith("postgresql://"):
    _db_url = "postgresql+psycopg://" + _db_url[len("postgresql://"):]
```

### Startup Migration Resilience

`backend-api/start.sh` retries `alembic upgrade head` up to 5 times (5-second delays) before starting uvicorn regardless. Additionally, `main.py`'s lifespan runs `CREATE TABLE IF NOT EXISTS agent_traces` as a fallback to ensure the traces table always exists.

---

## 14. Local Development

### Prerequisites

| Tool | Version |
|---|---|
| Docker | 24+ |
| Docker Compose | v2 |
| Node.js | 22 LTS |
| Python | 3.12 |

### Start Everything

```bash
# 1. Copy and configure environment
cp .env.example .env
# Edit .env — minimum: set ANTHROPIC_API_KEY

# 2. Start all services
docker compose up --build

# 3. Run database migrations (separate terminal)
docker compose exec backend-api alembic upgrade head
```

Services:

| Service | URL |
|---|---|
| Frontend | http://localhost:3000 |
| Backend API + Swagger | http://localhost:8000/docs |
| Agent Service | http://localhost:8001/docs |
| Notification Service | http://localhost:8002/docs |

### Run Individually

```bash
# backend-api
cd backend-api && pip install -r requirements.txt
export DATABASE_URL=postgresql://loan_user:changeme@localhost:5432/loan_db
export REDIS_STREAMS_URL=redis://localhost:6379/0
export REDIS_CELERY_URL=redis://localhost:6379/1
uvicorn main:app --port 8000 --reload

# agent-service FastAPI
cd agent-service && pip install -r requirements.txt
export DATABASE_URL=postgresql://...
export REDIS_STREAMS_URL=redis://localhost:6379/0
export REDIS_CELERY_URL=redis://localhost:6379/1
export ANTHROPIC_API_KEY=sk-ant-...
uvicorn main:app --port 8001 --reload

# agent-service Celery worker
celery -A worker.celery_app worker --loglevel=info --concurrency=2 -Q agent

# agent-service Celery Beat (monitoring scheduler)
celery -A worker.celery_app beat --loglevel=info

# frontend
cd frontend && npm install && npm run dev
```

---

## 15. Environment Variables

| Variable | Service | Required | Description |
|---|---|---|---|
| `ANTHROPIC_API_KEY` | agent-service, backend-api | Yes | Claude API key |
| `DATABASE_URL` | all | Yes | PostgreSQL connection string |
| `REDIS_STREAMS_URL` | all | Yes | Redis DB0 (event bus) |
| `REDIS_CELERY_URL` | agent-service, backend-api | Yes | Redis DB1 (Celery broker) |
| `REDIS_CACHE_URL` | agent-service | No | Redis DB2 (cache) |
| `BACKEND_URL` | frontend (nginx) | Yes | Internal URL to backend-api |
| `HITL_THRESHOLD` | agent-service | No | Loan amount (₹) above which RM HITL is required (default: 200000) |
| `SERVICE` | agent-service | No | `worker` or `beat` — selects Celery role |
| `NOTIFICATION_SERVICE_URL` | agent-service | No | URL to notification-service |
| `TWILIO_ACCOUNT_SID` | notification-service | Notifications | Twilio SID |
| `TWILIO_AUTH_TOKEN` | notification-service | Notifications | Twilio token |
| `TWILIO_FROM_NUMBER` | notification-service | Notifications | SMS sender number |
| `SENDGRID_API_KEY` | notification-service | Notifications | SendGrid API key |

---

## 16. API Reference

### Applications

```
POST   /api/v1/applications/              Submit a new application
GET    /api/v1/applications/              List applications (paginated, filterable)
GET    /api/v1/applications/{id}          Full application record
GET    /api/v1/applications/{id}/status   Status + stage summary
GET    /api/v1/applications/{id}/events   Audit log (timeline events)
GET    /api/v1/applications/{id}/traces   Agent reasoning traces (requires migration 0007)
```

### Documents

```
POST   /api/v1/documents/{id}/upload      Upload KYC document; triggers pipeline resume if kyc_pending
GET    /api/v1/documents/{id}             List uploaded documents
```

### Assessment

```
POST   /api/v1/assessment/{app_id}/start         Start assessment session
GET    /api/v1/assessment/session/{sid}           Get session info
WS     /api/v1/assessment/ws/{sid}                Chat WebSocket
POST   /api/v1/assessment/{sid}/finalize          Finalize and act on result
```

### RM Dashboard

```
GET    /api/v1/rm/queue                   Applications pending HITL review
GET    /api/v1/rm/{id}                    Application detail for RM
POST   /api/v1/rm/{id}/decision           Submit approve/reject decision
```

### Analytics

```
GET    /api/v1/analytics/overview         Total/approved/rejected counts
GET    /api/v1/analytics/pipeline         Applications per stage
GET    /api/v1/analytics/agents           Per-stage rejection rates + HITL queue depth
GET    /api/v1/analytics/background-agents Monitoring + outreach + pipeline activity
GET    /api/v1/analytics/evaluation       Per-node LLM call counts, latency, token usage
GET    /api/v1/analytics/traces-health    Diagnostic: agent_traces table status
POST   /api/v1/analytics/trigger-monitoring  Manually enqueue monitoring_scan
```

### WebSocket

```
WS     /ws/{application_id}               Subscribe to live pipeline events
```

---

## 17. Database Migrations

Migrations live in `backend-api/db/migrations/versions/` and are managed by Alembic.

| Migration | Description |
|---|---|
| `0001` | Create `applications` table |
| `0002` | Create `audit_logs` table |
| `0003` | Create `documents` table |
| `0004` | Create `rm_reviews` table |
| `0005` | Add applicant financial fields |
| `0006` | Add lead generation fields |
| `0007` | Create `agent_traces` table + indexes |

```bash
# Apply all pending migrations
alembic upgrade head

# Roll back one step
alembic downgrade -1

# Check current version
alembic current

# Create a new migration
alembic revision --autogenerate -m "description"
```
