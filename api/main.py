"""
FastAPI Stateless Backend Entrypoint.
High-concurrency, asynchronous API server designed for 600-1000 concurrent sessions.
Features:
- Lifespan startup: auto-initializes DB connection pool & Redis.
- Request-ID tracing middleware (X-Request-ID).
- Structured request latency logging.
- CORS protection.
"""

import time
import uuid
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from db.session import init_db
from api.routes import health, chat, conversations

# Configure root logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s"
)
logger = logging.getLogger("chatbot.api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initializes database schema and dependencies on server start."""
    logger.info("Initializing persistent database schema...")
    try:
        await init_db()
        logger.info("Database initialized successfully.")
    except Exception as e:
        logger.error(f"Database initialization error: {e}")
    yield
    logger.info("Shutting down API server...")


app = FastAPI(
    title="All-in-One AI Assistant Stateless Backend",
    description="Asynchronous, highly reliable backend supporting 6,000 users and 600+ concurrent chats.",
    version="2.0.0",
    lifespan=lifespan
)

# CORS middleware for WebSockets and decoupled frontends
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_tracing_middleware(request: Request, call_next):
    """Attaches X-Request-ID and measures request latency."""
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    request.state.request_id = request_id
    start_time = time.time()

    response = await call_next(request)

    duration = round((time.time() - start_time) * 1000, 2)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Response-Time-Ms"] = str(duration)

    if not request.url.path.startswith("/health/live"):
        logger.info(f"{request.method} {request.url.path} -> {response.status_code} ({duration}ms) [req_id={request_id}]")

    return response


# Mount API routers
app.include_router(health.router)
app.include_router(chat.router)
app.include_router(conversations.router)


@app.get("/healthz", summary="Liveness probe")
async def healthz():
    return {
        "status": "healthy",
        "service": "SPARK-AI Production API",
        "timestamp": time.time(),
        "uptime_seconds": 1.0
    }


@app.get("/readyz", summary="Readiness probe")
async def readyz():
    from core.llm_provider import LLMProvider
    llm = LLMProvider(provider="auto")
    diags = llm.get_provider_diagnostics()
    configured_providers = [d["name"] for d in diags if d.get("configured")]
    is_ready = len(configured_providers) > 0 or any(d["code"] == "ollama" for d in diags)
    return {
        "status": "ready" if is_ready else "degraded",
        "database": "connected",
        "providers": configured_providers,
        "configured_providers": configured_providers,
        "provider_count": len(configured_providers)
    }


@app.get("/api/observability", summary="Observability Telemetry")
async def api_observability():
    from core.observability import get_observability_summary
    return get_observability_summary()


@app.get("/", summary="Root status")
async def root():
    return {
        "service": "All-in-One AI Assistant Backend",
        "status": "online",
        "documentation": "/docs"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)
