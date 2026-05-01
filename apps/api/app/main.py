"""
AI Workspace API — FastAPI Application Entry Point

Configures the application with CORS, lifespan events,
and router registration.
"""

from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import chat, rag, agent, documents, workspaces


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """
    Application lifespan handler.

    Runs setup on startup and cleanup on shutdown.
    Database connections, Redis pools, and vector store
    clients will be initialized here in Phase 2.
    """
    # ── Startup ──────────────────────────────────────────────────────
    print(f"🚀 AI Workspace API starting in {settings.app_env} mode")
    yield
    # ── Shutdown ─────────────────────────────────────────────────────
    print("👋 AI Workspace API shutting down")


app = FastAPI(
    title="AI Workspace API",
    description="Fullstack AI system with RAG & Agents",
    version="0.1.0",
    lifespan=lifespan,
)

# ── CORS ─────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ──────────────────────────────────────────────────────────────
app.include_router(chat.router, prefix="/api/chat", tags=["Chat"])
app.include_router(rag.router, prefix="/api/rag", tags=["RAG"])
app.include_router(agent.router, prefix="/api/agent", tags=["Agent"])
app.include_router(documents.router, prefix="/api/documents", tags=["Documents"])
app.include_router(workspaces.router, prefix="/api/workspaces", tags=["Workspaces"])


@app.get("/health", tags=["Health"])
async def health_check() -> dict:
    """Health check endpoint for monitoring and container orchestration."""
    return {
        "status": "healthy",
        "service": "ai-workspace-api",
        "version": "0.1.0",
        "environment": settings.app_env,
    }
