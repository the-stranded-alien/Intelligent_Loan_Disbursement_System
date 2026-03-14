import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config.settings import settings
from routers import applications, analytics, documents, rm, webhooks, websocket
from services.event_consumer import EventConsumer

consumer = EventConsumer()


@asynccontextmanager
async def lifespan(app: FastAPI):
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


@app.get("/health", tags=["health"])
async def health_check():
    return {"status": "ok", "service": "backend-api"}
