---
description: Scaffold the full Intelligent Loan Disbursement System project structure
---

## Context

- Current directory contents: !`ls -la`
- Git status: !`git status --short`

## Your task

Scaffold the complete Intelligent Loan Disbursement System based on the InitialPlan.md in this repository.

Read `InitialPlan.md` first to understand the full project layout, then create **all** directories and starter files in one pass.

### What to create

#### Root level
- `docker-compose.yml` — all 9 services: postgres, redis, backend-api (8000), agent-service (8001), agent-worker, notification-service (8002), notification-worker, celery-beat, frontend (3000)
- `.env.example` — every variable from the `.env reference` section of InitialPlan.md
- `.gitignore` — Python, Node, Docker, .env

#### `backend-api/`
- `Dockerfile` (Python 3.11, uvicorn)
- `requirements.txt` (fastapi, uvicorn, sqlalchemy, alembic, psycopg2-binary, redis, python-jose, python-multipart, pydantic-settings)
- `main.py` (FastAPI app with router includes)
- `routers/applications.py`, `routers/webhooks.py`, `routers/documents.py`, `routers/rm.py`, `routers/websocket.py`, `routers/analytics.py`
- `schemas/application.py`, `schemas/rm.py`, `schemas/events.py`
- `services/event_publisher.py`, `services/event_consumer.py`, `services/websocket_manager.py`, `services/storage_service.py`
- `db/models.py` (Application, HITLReview, AuditLog, Document SQLAlchemy models), `db/repositories.py`, `db/migrations/env.py`
- `middleware/auth.py` (JWT bearer)
- `config/settings.py` (Pydantic BaseSettings)

#### `agent-service/`
- `Dockerfile`, `requirements.txt` (fastapi, celery, redis, langgraph, langchain-anthropic, psycopg2-binary, pgvector, jinja2, pydantic-settings)
- `main.py`
- `consumers/event_consumer.py`
- `worker/celery_app.py`, `worker/tasks.py` (run_pipeline, resume_pipeline, retry_disbursement)
- `graph/graph.py` (StateGraph with all 9 nodes), `graph/state.py` (ApplicationState TypedDict), `graph/checkpointer.py`, `graph/router.py`
- Agent stubs for all 9 agents, each with `agent.py` and `tools.py`:
  - `agents/lead_capture/`
  - `agents/lead_qualification/`
  - `agents/identity_verification/`
  - `agents/credit_assessment/`
  - `agents/fraud_detection/`
  - `agents/compliance/`
  - `agents/document_collection/`
  - `agents/sanction_processing/`
  - `agents/disbursement/`
- `services/event_publisher.py`, `services/ocr_service.py`, `services/embedding_service.py`
- `config/settings.py`
- `config/prompts/` — one `.j2` file per agent node (lead_qualification, identity_verification, credit_assessment, fraud_detection, compliance, document_collection, sanction_processing, disbursement)

#### `notification-service/`
- `Dockerfile`, `requirements.txt` (fastapi, celery, redis, twilio, sendgrid, jinja2, pydantic-settings)
- `main.py`
- `consumers/event_consumer.py`
- `worker/celery_app.py`, `worker/tasks.py`, `worker/beat_schedule.py`
- `handlers/` — one handler per event type
- `templates/sms/`, `templates/whatsapp/`, `templates/email/` — placeholder Jinja2 templates
- `services/twilio_service.py`, `services/sendgrid_service.py`
- `config/settings.py`

#### `frontend/`
- `Dockerfile` (node:20-alpine, vite build)
- `package.json` (react 18, typescript, vite, shadcn/ui, tailwindcss, zustand, recharts, react-hook-form, zod)
- `tsconfig.json`, `vite.config.ts`, `tailwind.config.ts`, `index.html`
- `src/pages/ApplicationForm.tsx`, `src/pages/StatusTracker.tsx`, `src/pages/RMDashboard.tsx`, `src/pages/Analytics.tsx`
- `src/components/WorkflowTimeline.tsx`, `src/components/AgentDecisionCard.tsx`, `src/components/WhatIfAnalysis.tsx`, `src/components/NotificationFeed.tsx`
- `src/hooks/useWorkflowSocket.ts`
- `src/store/applicationStore.ts`

### Rules
- Every file must have a meaningful stub — no empty files. Add imports, type stubs, and TODO comments.
- Use `pass` / `...` for unimplemented Python functions; use empty component bodies with a `// TODO` for React.
- Follow the exact path names from InitialPlan.md.
- After creating all files, run `git status --short` and confirm the count of new files.
- Do NOT run `docker compose up` — just create the files.
