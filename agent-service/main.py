import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI

from config.settings import settings
from consumers.event_consumer import AgentEventConsumer

logger = logging.getLogger(__name__)
consumer = AgentEventConsumer()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await consumer.connect()
    task = asyncio.create_task(consumer.consume())
    yield
    consumer._running = False
    task.cancel()
    await consumer.close()


app = FastAPI(
    title="Loan Agent Service",
    description="LangGraph pipeline service for the Intelligent Loan Disbursement System",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health", tags=["health"])
async def health_check():
    return {"status": "ok", "service": "agent-service"}
