"""DataGuard — Risk-Aware Autonomous Data Quality Operations.

FastAPI application entry point.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from apps.api.config import settings

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown."""
    # Startup
    logger.info("DataGuard starting up...")
    Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
    Path(settings.version_dir).mkdir(parents=True, exist_ok=True)
    yield
    # Shutdown
    logger.info("DataGuard shutting down...")


app = FastAPI(
    title="DataGuard API",
    description=(
        "Risk-Aware Autonomous Data Quality Operations. "
        "An evidence-driven AI data-operations worker that knows "
        "when it can act, when it must ask, and when it must refuse."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

# ── CORS ──
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Health Check ──
@app.get("/health", tags=["system"])
async def health_check():
    """Health check endpoint for monitoring and deployment verification."""
    return {
        "status": "healthy",
        "service": "DataGuard",
        "version": "0.1.0",
    }


# ── Root ──
@app.get("/", tags=["system"])
async def root():
    """Root endpoint with system information."""
    return {
        "name": "DataGuard",
        "description": "Risk-Aware Autonomous Data Quality Operations",
        "version": "0.1.0",
        "docs": "/docs",
        "thesis": "Uncertainty is not something the AI should hide. It is a routing signal.",
    }


# ── Import and register routers ──
from apps.api.routers import datasets, verify, reviews, audit, chat

app.include_router(datasets.router, prefix="/api")
app.include_router(verify.router, prefix="/api")
app.include_router(reviews.router, prefix="/api")
app.include_router(audit.router, prefix="/api")
app.include_router(chat.router, prefix="/api")



# ── System stats ──
@app.get("/api/stats", tags=["system"])
async def system_stats():
    """Get system statistics including LLM cost tracking."""
    from core.llm.client import get_cost_summary
    from apps.api.routers.datasets import _datasets, _analysis_results

    total_decisions = sum(
        len(r.get("decisions", []))
        for r in _analysis_results.values()
    )
    total_auto = sum(
        r.get("summary", {}).get("auto_count", 0)
        for r in _analysis_results.values()
    )
    total_esc = sum(
        r.get("summary", {}).get("escalate_count", 0)
        for r in _analysis_results.values()
    )

    return {
        "datasets_count": len(_datasets),
        "total_decisions": total_decisions,
        "auto_count": total_auto,
        "escalate_count": total_esc,
        "automation_rate": round(total_auto / total_decisions, 4) if total_decisions > 0 else 0,
        "llm_cost": get_cost_summary(),
    }


# ── Global exception handler ──
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_server_error",
            "message": "An unexpected error occurred. Please try again.",
        },
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "apps.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
    )
