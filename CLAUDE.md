# Intelligent Loan Disbursement System

Agentic AI system for automated loan processing using LangGraph, FastAPI, and Claude.

## Tech Stack

- **Orchestration**: LangGraph (9-node state machine) + Claude `claude-sonnet-4-6`
- **Backend**: FastAPI (Python 3.11) — `backend-api` (port 8000), `agent-service` (port 8001), `notification-service` (port 8002)
- **Workers**: Celery (`agent-worker`, `notification-worker`, `celery-beat`)
- **DB**: PostgreSQL 16 + pgvector (applications, checkpoints, RAG embeddings)
- **Events**: Redis Streams (DB0) as inter-service bus; Celery broker on Redis DB1; cache on Redis DB2
- **Frontend**: React 18 + TypeScript + shadcn/ui + Zustand (port 3000)

## Project Layout

See `InitialPlan.md` for the full directory tree and service descriptions.

Key paths:
- `agent-service/graph/` — LangGraph graph, state, checkpointer, router
- `agent-service/agents/` — 9 agent nodes (lead_capture → disbursement)
- `agent-service/config/prompts/` — Jinja2 `.j2` prompt templates
- `backend-api/routers/` — REST endpoints (apply, status, rm, documents, analytics)
- `notification-service/` — event-driven notifications via Twilio + SendGrid

## Available Skills (Slash Commands)

| Command | Description |
|---|---|
| `/scaffold` | Create the full project structure from InitialPlan.md |
| `/dev` | Start all Docker services with health checks |
| `/migrate [up\|down\|status\|new <msg>]` | Alembic DB migrations |
| `/seed-rag` | Seed pgvector with compliance policy embeddings |
| `/test-agent <node>` | Test a single LangGraph agent node in isolation |
| `/test-all` | Run the full test suite across all services |
| `/trace-pipeline [app_id\|new]` | Trace an application through the 9-node pipeline |
| `/hitl <app_id> approve\|reject` | Process an RM HITL review |
| `/status` | System health dashboard (services, metrics, Redis, Celery) |
| `/logs <service\|all\|errors>` | Tail Docker service logs |
| `/add-agent <name>` | Add a new agent node to the LangGraph pipeline |
| `/add-notification <event> <channel>` | Add a new notification template + task |
| `/prompt <node>` | View, edit, or test a Jinja2 prompt template |
| `/event [list\|inspect\|replay\|publish]` | Inspect and debug Redis Streams events |

## Key Conventions

- All agent nodes follow the pattern: `async def run_<node>(state: ApplicationState) -> ApplicationState`
- Prompts are Jinja2 templates in `agent-service/config/prompts/<node>.j2` — output must be JSON
- Events are published to Redis Streams, not called directly between services
- LangGraph checkpoints use `PostgresSaver` — every node completion is persisted
- HITL interrupt is used in `sanction_processing` for loans > ₹10L
- Celery retry pattern for disbursement: immediate → 1h → 4h → 24h

## Environment

Copy `.env.example` to `.env` and fill in:
- `ANTHROPIC_API_KEY` — required for all LLM calls
- `DATABASE_URL` — PostgreSQL connection string
- `REDIS_STREAMS_URL`, `REDIS_CELERY_URL`, `REDIS_CACHE_URL`
- `TWILIO_*`, `SENDGRID_API_KEY`, `GOOGLE_DOC_AI_PROJECT`
