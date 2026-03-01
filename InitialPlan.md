# Intelligent Loan Disbursement System — Local Dev Plan

---

## Tech Stack

### Agentic AI / GenAI Core

| Component | Choice | Purpose |
|---|---|---|
| **Orchestration** | LangGraph | 9-node state machine, conditional routing, HITL interrupts, checkpointing |
| **LLM** | Claude `claude-sonnet-4-6` | Reasoning, tool calling, decision-making per agent node |
| **Checkpointing** | LangGraph `PostgresSaver` | Persist graph state after every node; resume on failure or HITL |
| **RAG** | pgvector (Postgres extension) | Semantic search over RBI guidelines, AML rules, lending policy |
| **Prompt Templates** | Jinja2 `.j2` files | One versioned prompt per agent node |

### Services

| Service | Framework | Purpose |
|---|---|---|
| **backend-api** | FastAPI (Python 3.11) | Public-facing — REST, WebSockets, file uploads, HITL routes |
| **agent-service** | FastAPI (Python 3.11) | Internal — Redis Streams consumer, enqueues Celery pipeline tasks |
| **agent-worker** | Celery | Executes LangGraph pipeline tasks asynchronously |
| **notification-service** | FastAPI (Python 3.11) | Internal — Redis Streams consumer, enqueues Celery notification tasks |
| **notification-worker** | Celery | Sends SMS / WhatsApp / Email |
| **celery-beat** | Celery Beat | Scheduled jobs — doc reminders, RM follow-ups, sanction nudges |
| **frontend** | React 18 + TypeScript | SPA — application form, live tracker, RM dashboard, analytics |

### Frontend Libraries

| Component | Choice |
|---|---|
| **UI** | shadcn/ui + TailwindCSS |
| **State** | Zustand |
| **Real-time** | WebSocket (via backend-api) |
| **Charts** | Recharts |
| **Forms** | React Hook Form + Zod |

### Infrastructure

| Component | Choice | Purpose |
|---|---|---|
| **PostgreSQL 16 + pgvector** | Primary DB | Applications, decisions, audit logs, LangGraph checkpoints, RAG embeddings |
| **Redis DB0** | Redis Streams | Event bus — all inter-service async communication |
| **Redis DB1** | Celery broker + backend | Task queues for agent-worker and notification-worker |
| **Redis DB2** | Cache + pub/sub | WebSocket state, response cache |

### External APIs

| API | Used By | Purpose |
|---|---|---|
| Anthropic API | agent-worker | LLM calls per agent node |
| Google Document AI | agent-worker | OCR for PAN, income proof, bank statements |
| Twilio | notification-worker | SMS + WhatsApp |
| SendGrid | notification-worker | Email |

---

## Docker Services

```
postgres              → port 5432
redis                 → port 6379
backend-api           → port 8000
agent-service         → port 8001   (internal only)
agent-worker          → no port     (Celery worker)
notification-service  → port 8002   (internal only)
notification-worker   → no port     (Celery worker)
celery-beat           → no port     (scheduler)
frontend              → port 3000
```

---

## Event Catalog (Redis Streams)

| Event | Producer | Consumers |
|---|---|---|
| `application.created` | backend-api | agent-service |
| `node.completed` | agent-worker | backend-api, notification-service |
| `hitl.requested` | agent-worker | backend-api, notification-service |
| `pipeline.paused` | agent-worker | backend-api, notification-service |
| `hitl.approved` | backend-api | agent-service |
| `hitl.rejected` | backend-api | agent-service |
| `pipeline.completed` | agent-worker | backend-api, notification-service |
| `pipeline.rejected` | agent-worker | backend-api, notification-service |

---

## Celery Task Catalog

### agent-worker

| Task | Trigger | Purpose |
|---|---|---|
| `run_pipeline` | `application.created` event | Runs full LangGraph graph from Node 1 |
| `resume_pipeline` | `hitl.approved / rejected` event | Resumes graph from Postgres checkpoint |
| `retry_disbursement` | Node 9 failure edge | Retries bank transfer — immediate → 1h → 4h → 24h |

### notification-worker

| Task | Trigger | Purpose |
|---|---|---|
| `send_stage_notification` | `node.completed` | Stage update SMS/email to applicant |
| `send_rejection_notification` | `pipeline.rejected` | Rejection with improvement guidance |
| `send_disbursement_confirmation` | `pipeline.completed` | Success + EMI schedule |
| `send_rm_hitl_alert` | `hitl.requested` | RM alert — review required |
| `send_document_reminder` | Celery Beat (24h / 48h / 72h) | Escalating doc submission reminders |
| `send_rm_followup` | Celery Beat (5 days stalled) | RM personal follow-up assignment |
| `send_sanction_reminder` | Celery Beat (48h after sanction) | Nudge applicant to accept terms |

---

## Project Structure

```
intelligent-loan-system/
│
├── docker-compose.yml
├── .env
├── README.md
│
├── backend-api/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py
│   ├── routers/
│   │   ├── applications.py              # POST /apply, GET /status/{id}
│   │   ├── webhooks.py                  # Inbound leads — SMS, WhatsApp, marketing
│   │   ├── documents.py                 # POST /documents/upload
│   │   ├── rm.py                        # GET /rm/queue, POST /rm/approve/{id}, /rm/reject/{id}
│   │   ├── websocket.py                 # WS /ws/{application_id}
│   │   └── analytics.py                 # GET /analytics/pipeline, /analytics/agents
│   ├── schemas/
│   │   ├── application.py
│   │   ├── rm.py
│   │   └── events.py                    # Typed event payload schemas
│   ├── services/
│   │   ├── event_publisher.py           # Redis Streams publish wrapper
│   │   ├── event_consumer.py            # Streams consumer → WebSocket broadcast
│   │   ├── websocket_manager.py         # Active WS connections per app_id
│   │   └── storage_service.py           # Local file storage
│   ├── db/
│   │   ├── models.py                    # Application, HITLReview, AuditLog, Document
│   │   ├── repositories.py
│   │   └── migrations/                  # Alembic
│   ├── middleware/
│   │   └── auth.py                      # JWT bearer token
│   └── config/
│       └── settings.py                  # Pydantic BaseSettings
│
├── agent-service/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py                          # FastAPI + starts Streams consumer loop
│   ├── consumers/
│   │   └── event_consumer.py            # Consumes application.created, hitl.approved/rejected
│   │                                    # → enqueues Celery tasks
│   ├── worker/
│   │   ├── celery_app.py                # Celery app (broker = redis DB1)
│   │   └── tasks.py                     # run_pipeline(), resume_pipeline(), retry_disbursement()
│   ├── graph/
│   │   ├── graph.py                     # StateGraph — all 9 nodes + edges + conditions
│   │   ├── state.py                     # ApplicationState TypedDict
│   │   ├── checkpointer.py              # PostgresSaver setup
│   │   └── router.py                    # Conditional edge functions
│   ├── agents/
│   │   ├── lead_capture/
│   │   │   ├── agent.py
│   │   │   └── tools.py                 # channel_parser_tool, schema_normalizer_tool
│   │   ├── lead_qualification/
│   │   │   ├── agent.py
│   │   │   └── tools.py                 # pan_validator_tool, income_threshold_tool, kyc_tool
│   │   ├── identity_verification/
│   │   │   ├── agent.py
│   │   │   └── tools.py                 # ocr_tool, face_match_tool
│   │   ├── credit_assessment/
│   │   │   ├── agent.py
│   │   │   └── tools.py                 # cibil_tool, experian_tool, account_aggregator_tool
│   │   ├── fraud_detection/
│   │   │   ├── agent.py
│   │   │   └── tools.py                 # hash_dedup_tool, fraud_score_tool, device_fp_tool
│   │   ├── compliance/
│   │   │   ├── agent.py
│   │   │   └── tools.py                 # aml_tool, pep_screening_tool, policy_rag_tool
│   │   ├── document_collection/
│   │   │   ├── agent.py
│   │   │   └── tools.py                 # doc_status_tool, reminder_trigger_tool
│   │   ├── sanction_processing/
│   │   │   ├── agent.py                 # interrupt() for loans > ₹10L
│   │   │   └── tools.py                 # sanction_letter_gen_tool, risk_pricing_tool
│   │   └── disbursement/
│   │       ├── agent.py
│   │       └── tools.py                 # bank_verify_tool, payment_gateway_tool
│   ├── services/
│   │   ├── event_publisher.py           # Publishes node/pipeline events to Redis Streams
│   │   ├── ocr_service.py               # Google Document AI wrapper
│   │   └── embedding_service.py         # pgvector upsert for compliance RAG
│   └── config/
│       ├── settings.py
│       └── prompts/
│           ├── lead_qualification.j2
│           ├── identity_verification.j2
│           ├── credit_assessment.j2
│           ├── fraud_detection.j2
│           ├── compliance.j2
│           ├── document_collection.j2
│           ├── sanction_processing.j2
│           └── disbursement.j2
│
├── notification-service/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py                          # FastAPI (health only) + starts Streams consumer loop
│   ├── consumers/
│   │   └── event_consumer.py            # Consumes pipeline events → enqueues Celery tasks
│   ├── worker/
│   │   ├── celery_app.py                # Celery app (broker = redis DB1)
│   │   ├── tasks.py                     # All send_* notification tasks
│   │   └── beat_schedule.py             # Celery Beat schedule definitions
│   ├── handlers/
│   │   ├── node_completed_handler.py
│   │   ├── pipeline_rejected_handler.py
│   │   ├── pipeline_completed_handler.py
│   │   ├── hitl_requested_handler.py
│   │   └── pipeline_paused_handler.py
│   ├── templates/
│   │   ├── sms/
│   │   ├── whatsapp/
│   │   └── email/
│   ├── services/
│   │   ├── twilio_service.py
│   │   └── sendgrid_service.py
│   └── config/
│       └── settings.py
│
└── frontend/
    ├── Dockerfile
    ├── package.json
    └── src/
        ├── pages/
        │   ├── ApplicationForm.tsx      # Multi-step loan intake
        │   ├── StatusTracker.tsx        # Live 9-stage pipeline progress
        │   ├── RMDashboard.tsx          # HITL queue — risk summary + approve/reject
        │   └── Analytics.tsx            # Pipeline metrics, agent decisions
        ├── components/
        │   ├── WorkflowTimeline.tsx     # Visual 9-node pipeline with live status
        │   ├── AgentDecisionCard.tsx    # LLM reasoning display per node
        │   ├── WhatIfAnalysis.tsx       # Loan amount adjustment → risk impact
        │   └── NotificationFeed.tsx     # Recent comms per application
        ├── hooks/
        │   └── useWorkflowSocket.ts     # WS hook → dispatches to Zustand store
        └── store/
            └── applicationStore.ts      # Zustand — pipeline stages, RM queue, analytics
```

---

## Initial Setup

### 1. Clone & configure environment

```bash
git clone https://github.com/your-org/intelligent-loan-system.git
cd intelligent-loan-system
cp .env.example .env
# Fill in: ANTHROPIC_API_KEY, TWILIO_*, SENDGRID_API_KEY, GOOGLE_DOC_AI_PROJECT
```

### 2. `.env` reference

```bash
# LLM
ANTHROPIC_API_KEY=sk-ant-...

# Database
DATABASE_URL=postgresql://loan_user:password@postgres:5432/loan_db

# Redis
REDIS_STREAMS_URL=redis://redis:6379/0
REDIS_CELERY_URL=redis://redis:6379/1
REDIS_CACHE_URL=redis://redis:6379/2

# Auth
JWT_SECRET=local-dev-secret-change-in-prod

# External APIs
GOOGLE_DOC_AI_PROJECT=your-gcp-project
TWILIO_ACCOUNT_SID=AC...
TWILIO_AUTH_TOKEN=...
SENDGRID_API_KEY=SG...

# Redis Stream names
STREAM_APPLICATION_CREATED=application.created
STREAM_NODE_COMPLETED=node.completed
STREAM_HITL_REQUESTED=hitl.requested
STREAM_PIPELINE_PAUSED=pipeline.paused
STREAM_HITL_APPROVED=hitl.approved
STREAM_HITL_REJECTED=hitl.rejected
STREAM_PIPELINE_COMPLETED=pipeline.completed
STREAM_PIPELINE_REJECTED=pipeline.rejected

# Consumer group names
CONSUMER_GROUP_AGENT=agent-service-group
CONSUMER_GROUP_NOTIFICATION=notification-service-group
CONSUMER_GROUP_BACKEND=backend-api-group
```

### 3. Start all services

```bash
docker compose up --build
```

### 4. Run database migrations

```bash
docker compose exec backend-api alembic upgrade head
```

### 5. Seed compliance policy embeddings (for RAG)

```bash
docker compose exec agent-service python -m scripts.seed_embeddings
# Ingests RBI guidelines, AML rules, internal policy docs into pgvector
```

---

## What Gets Added Later (Production)

| Local (Now) | Production (Later) |
|---|---|
| Redis Streams | Apache Kafka |
| Redis single instance | Dedicated Redis cluster per use |
| Local volume (files) | GCS / S3 |
| Simple JWT middleware | Keycloak (OAuth2/OIDC) |
| Direct service URLs | API Gateway (Kong / Traefik) |
| Docker Compose | Kubernetes (GKE / EKS) |
| Single Postgres | Postgres HA + read replicas |
| Mock external APIs | Real CIBIL, Experian, AA integrations |