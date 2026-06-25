"""
AgentOS FastAPI Gateway
"""

import os
import time
import uuid
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

from gateway.config import get_settings
from gateway.database import init_db
from gateway.observability.logging_setup import setup_logging
from gateway.observability.metrics import registry, ACTIVE_SESSIONS

# Routers
from gateway.routers import auth, sessions, messages, documents, metrics_router, ws

logger = structlog.get_logger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    setup_logging()
    await init_db()
    logger.info("agentos_started", environment=settings.environment)
    yield
    # Shutdown
    logger.info("agentos_shutting_down")


app = FastAPI(
    title="AgentOS",
    description="Production Multi-Agent RAG Platform",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ─── Middleware ────────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    """Attach unique request ID to every request for tracing."""
    request_id = str(uuid.uuid4())
    structlog.contextvars.bind_contextvars(request_id=request_id)
    request.state.request_id = request_id

    t0 = time.monotonic()
    response = await call_next(request)
    latency_ms = (time.monotonic() - t0) * 1000

    response.headers["X-Request-ID"] = request_id
    response.headers["X-Latency-Ms"] = str(round(latency_ms, 1))

    logger.info(
        "http_request",
        method=request.method,
        path=request.url.path,
        status=response.status_code,
        latency_ms=round(latency_ms, 1),
    )
    structlog.contextvars.clear_contextvars()
    return response


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    """Per-user rate limiting via Redis."""
    from gateway.cache import rate_limit_check

    # Skip rate limiting for non-API routes
    if not request.url.path.startswith("/api/"):
        return await call_next(request)

    # Get user ID from header (set by auth layer) or IP
    user_id = request.headers.get("X-User-ID", request.client.host if request.client else "anon")
    allowed = await rate_limit_check(user_id, limit=settings.rate_limit_per_minute)

    if not allowed:
        return JSONResponse(
            status_code=429,
            content={"detail": "Rate limit exceeded. Try again in a minute."},
        )
    return await call_next(request)


# ─── Routers ──────────────────────────────────────────────────────────────────

app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
app.include_router(sessions.router, prefix="/api/sessions", tags=["Sessions"])
app.include_router(messages.router, prefix="/api/messages", tags=["Messages"])
app.include_router(documents.router, prefix="/api/documents", tags=["Documents"])
app.include_router(metrics_router.router, prefix="/api/metrics", tags=["Metrics"])
app.include_router(ws.router, prefix="/ws", tags=["WebSocket"])


# ─── Health & Metrics ─────────────────────────────────────────────────────────

@app.get("/health", tags=["System"])
async def health():
    return {"status": "healthy", "version": "1.0.0"}


@app.get("/metrics", tags=["System"])
async def prometheus_metrics():
    return Response(
        content=generate_latest(registry),
        media_type=CONTENT_TYPE_LATEST,
    )


@app.get("/", tags=["System"])
async def root():
    return {
        "name": "AgentOS",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
    }
