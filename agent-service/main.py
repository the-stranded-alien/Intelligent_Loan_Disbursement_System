import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI

from consumers.event_consumer import AgentEventConsumer
from consumers.hitl_consumer import HitlDecisionConsumer
from routers import assessment, negotiation
from services.tracing import configure_tracing

logger = logging.getLogger(__name__)
consumer = AgentEventConsumer()
hitl_consumer = HitlDecisionConsumer()


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_tracing()
    await consumer.connect()
    await hitl_consumer.connect()
    task = asyncio.create_task(consumer.consume())
    hitl_task = asyncio.create_task(hitl_consumer.consume())
    yield
    consumer._running = False
    hitl_consumer._running = False
    task.cancel()
    hitl_task.cancel()
    await consumer.close()
    await hitl_consumer.close()


app = FastAPI(
    title="Loan Agent Service",
    description="LangGraph pipeline service for the Intelligent Loan Disbursement System",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(assessment.router, prefix="/api/v1/assessment", tags=["assessment"])
app.include_router(negotiation.router, prefix="/api/v1/negotiation", tags=["negotiation"])


@app.get("/health", tags=["health"])
async def health_check():
    return {"status": "ok", "service": "agent-service"}
