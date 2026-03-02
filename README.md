# Intelligent Loan Disbursement System

An agentic AI system for fully automated loan processing — from lead capture through to bank disbursement — powered by **LangGraph**, **FastAPI**, and **Claude claude-sonnet-4-6**.

---

## 1. Overview

The system processes loan applications through a **9-node LangGraph pipeline**, with each node backed by a Claude-powered agent:

1. **Lead Capture** — Validate and score incoming applicant data
2. **Lead Qualification** — Eligibility check against RBI policy (RAG-backed)
3. **Identity Verification** — PAN/Aadhaar KYC + Google Document AI OCR
4. **Credit Assessment** — Credit bureau analysis (CIBIL/Experian), DTI ratio
5. **Fraud Detection** — Velocity checks, ML risk scoring, duplicate detection
6. **Compliance** — AML, PEP, sanctions screening, RBI regulatory checks
7. **Document Collection** — Document checklist verification with OCR validation
8. **Sanction Processing** — Final loan terms calculation; HITL interrupt for loans > ₹10L
9. **Disbursement** — Bank transfer via payment rail; retry: immediate → 1h → 4h → 24h

---

## 2. Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Intelligent Loan Disbursement System                 │
└─────────────────────────────────────────────────────────────────────────────┘

  Browser (React 18 + TypeScript)
    │  :3000
    │
    ▼
  ┌──────────────────┐      REST / WebSocket
  │   frontend       │ ─────────────────────────────────┐
  │   (nginx)        │                                   │
  └──────────────────┘                                   ▼
                                              ┌─────────────────────┐
                                              │    backend-api      │ :8000
                                              │  (FastAPI + SQLAlch) │
                                              └──────────┬──────────┘
                                                         │ Redis Streams (DB0)
                                                         │
                              ┌──────────────────────────┼──────────────────────────┐
                              │                          │                          │
                              ▼                          ▼                          ▼
                   ┌──────────────────┐      ┌──────────────────┐      ┌──────────────────┐
                   │  agent-service   │      │ notification-svc │      │    PostgreSQL 16  │
                   │  :8001           │      │  :8002           │      │  + pgvector       │
                   │  LangGraph 9-node│      │  Twilio/SendGrid │      └──────────────────┘
                   │  pipeline        │      │                  │
                   └──────┬───────────┘      └──────────────────┘
                          │ Celery (Redis DB1)
                   ┌──────┴───────────────────────────┐
                   │                                   │
                   ▼                                   ▼
          ┌────────────────┐                ┌───────────────────┐
          │  agent-worker  │                │  notification-wkr │
          │  (Celery)      │                │  + celery-beat    │
          └────────────────┘                └───────────────────┘

  Shared Infrastructure:
  ┌──────────────────┐   ┌─────────────────────────────────────┐
  │  Redis 7.4       │   │  DB0: Streams  DB1: Celery  DB2: Cache│
  └──────────────────┘   └─────────────────────────────────────┘
```

---

## 3. Prerequisites

| Tool | Version |
|---|---|
| Docker | 24+ |
| Docker Compose | v2 |
| Node.js | 22 LTS |
| Python | 3.12 |
| make | any |

---

## 4. Quick Start

```bash
# 1. Clone and configure environment
cp .env.example .env
# Edit .env — at minimum set ANTHROPIC_API_KEY

# 2. Build and start all services
make build
make up

# 3. Run database migrations
make migrate
```

Services will be available at:

| Service | URL |
|---|---|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| Agent Service | http://localhost:8001 |
| Notification Service | http://localhost:8002 |
| API Docs (Swagger) | http://localhost:8000/docs |

---

## 5. Run Individual Services

### backend-api

```bash
cd backend-api
pip install -r requirements.txt

# Required env vars
export DATABASE_URL=postgresql://loan_user:changeme@localhost:5432/loan_db
export REDIS_STREAMS_URL=redis://localhost:6379/0
export SECRET_KEY=dev-secret-key

uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### agent-service

```bash
cd agent-service
pip install -r requirements.txt

export DATABASE_URL=postgresql://loan_user:changeme@localhost:5432/loan_db
export REDIS_STREAMS_URL=redis://localhost:6379/0
export REDIS_CELERY_URL=redis://localhost:6379/1
export ANTHROPIC_API_KEY=sk-ant-...

# FastAPI server
uvicorn main:app --host 0.0.0.0 --port 8001 --reload

# Celery worker (separate terminal)
celery -A worker.celery_app worker --loglevel=info --concurrency=4 -Q agent
```

### notification-service

```bash
cd notification-service
pip install -r requirements.txt

export REDIS_STREAMS_URL=redis://localhost:6379/0
export REDIS_CELERY_URL=redis://localhost:6379/1
export TWILIO_ACCOUNT_SID=...
export SENDGRID_API_KEY=...

# FastAPI server
uvicorn main:app --host 0.0.0.0 --port 8002 --reload

# Celery worker (separate terminal)
celery -A worker.celery_app worker --loglevel=info --concurrency=2 -Q notifications

# Celery beat scheduler (separate terminal)
celery -A worker.celery_app beat --loglevel=info
```

### frontend

```bash
cd frontend
npm install
npm run dev
# → http://localhost:3000
```

---

## 6. Environment Variables Reference

| Variable | Description | Required |
|---|---|---|
| `ANTHROPIC_API_KEY` | Claude API key | Yes |
| `DATABASE_URL` | PostgreSQL connection string | Yes |
| `REDIS_STREAMS_URL` | Redis DB0 (event bus) | Yes |
| `REDIS_CELERY_URL` | Redis DB1 (Celery broker) | Yes |
| `REDIS_CACHE_URL` | Redis DB2 (cache) | Yes |
| `SECRET_KEY` | JWT signing secret | Yes |
| `TWILIO_ACCOUNT_SID` | Twilio account SID | Notifications |
| `TWILIO_AUTH_TOKEN` | Twilio auth token | Notifications |
| `SENDGRID_API_KEY` | SendGrid API key | Notifications |
| `GOOGLE_DOC_AI_PROJECT` | GCP project for Document AI | OCR |
| `HITL_THRESHOLD` | Loan amount (₹) above which HITL is triggered | No (default: 1000000) |

See `.env.example` for the complete list.

---

## 7. Service URLs

| Service | Port | Health Check | API Docs |
|---|---|---|---|
| Frontend | 3000 | — | — |
| Backend API | 8000 | `GET /health` | `GET /docs` |
| Agent Service | 8001 | `GET /health` | `GET /docs` |
| Notification Service | 8002 | `GET /health` | `GET /docs` |
| PostgreSQL | 5432 | — | — |
| Redis | 6379 | — | — |

---

## 8. Database Migrations

```bash
# Apply all pending migrations
make migrate

# Roll back one migration
make migrate-down

# Check current migration version
make migrate-status

# Create a new migration (auto-generates from model changes)
make migrate-new
# → prompted for migration message
```

Migrations use **Alembic** and live in `backend-api/db/migrations/versions/`.

---

## 9. Seeding RAG Embeddings

The compliance knowledge base (RBI guidelines, AML rules, lending policy) must be embedded into pgvector before the pipeline can perform RAG queries:

```bash
make seed
# or directly:
docker compose exec agent-service python -m scripts.seed_rag
```

---

## 10. Available Slash Commands

These Claude Code skills are available in `.claude/commands/`:

| Command | Description |
|---|---|
| `/scaffold` | Regenerate the full project structure from `InitialPlan.md` |
| `/dev` | Start all Docker services with health checks |
| `/migrate [up\|down\|status\|new <msg>]` | Alembic DB migrations |
| `/seed-rag` | Seed pgvector with compliance policy embeddings |
| `/test-agent <node>` | Test a single LangGraph agent node in isolation |
| `/test-all` | Run the full test suite across all services |
| `/trace-pipeline [app_id\|new]` | Trace an application through all 9 nodes |
| `/hitl <app_id> approve\|reject` | Process an RM HITL review |
| `/status` | System health dashboard |
| `/logs <service\|all\|errors>` | Tail Docker service logs |
| `/add-agent <name>` | Add a new LangGraph agent node end-to-end |
| `/add-notification <event> <channel>` | Add a notification template + Celery task |
| `/prompt <node>` | View, edit, or test a Jinja2 prompt template |
| `/event [list\|inspect\|replay\|publish]` | Inspect and debug Redis Streams events |
