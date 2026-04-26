import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config.settings import settings
from routers import applications, analytics, documents, rm, webhooks, websocket, assessment_proxy
from services.event_consumer import EventConsumer

logger = logging.getLogger(__name__)
consumer = EventConsumer()


def _ensure_agent_traces_table() -> None:
    """Create agent_traces if alembic missed it (e.g. DB not ready during startup)."""
    from db.session import SessionLocal
    sql = """
    CREATE TABLE IF NOT EXISTS agent_traces (
        id              VARCHAR PRIMARY KEY,
        application_id  VARCHAR REFERENCES applications(id),
        agent_role      VARCHAR NOT NULL,
        node_name       VARCHAR NOT NULL,
        prompt_rendered TEXT,
        raw_llm_response TEXT,
        parsed_output   JSON,
        duration_ms     INTEGER,
        model           VARCHAR,
        input_tokens    INTEGER,
        output_tokens   INTEGER,
        created_at      TIMESTAMP
    );
    CREATE INDEX IF NOT EXISTS ix_agent_traces_application_id ON agent_traces(application_id);
    CREATE INDEX IF NOT EXISTS ix_agent_traces_node_name      ON agent_traces(node_name);
    """
    db = SessionLocal()
    try:
        db.execute(__import__("sqlalchemy").text(sql))
        db.commit()
        logger.info("agent_traces table verified/created")
    except Exception as e:
        logger.warning("agent_traces ensure failed (will retry on next restart): %s", e)
        db.rollback()
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    _ensure_agent_traces_table()
    await consumer.connect()
    task = asyncio.create_task(consumer.consume())
    yield
    consumer._running = False
    task.cancel()
    await consumer.close()


app = FastAPI(
    title="Loan Disbursement API",
    description="Backend API for the Intelligent Loan Disbursement System",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(applications.router, prefix="/api/v1/applications", tags=["applications"])
app.include_router(documents.router, prefix="/api/v1/documents", tags=["documents"])
app.include_router(rm.router, prefix="/api/v1/rm", tags=["rm"])
app.include_router(analytics.router, prefix="/api/v1/analytics", tags=["analytics"])
app.include_router(webhooks.router, prefix="/api/v1/webhooks", tags=["webhooks"])
app.include_router(websocket.router, prefix="/ws", tags=["websocket"])
app.include_router(assessment_proxy.router, prefix="/api/v1/assessment", tags=["assessment"])


@app.get("/health", tags=["health"])
async def health_check():
    return {"status": "ok", "service": "backend-api"}
