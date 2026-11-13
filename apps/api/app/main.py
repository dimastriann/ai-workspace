"""
AI Workspace API — FastAPI Application Entry Point

Configures the application with CORS, lifespan events,
and router registration.
"""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.core.database import async_session
from app.models.enums import Role
from app.routers import (
    agent,
    auth,
    chat,
    documents,
    rag,
    skills,
    users,
    workspaces,
)
from app.routers import (
    settings as settings_router,
)
from app.services.auth_service import auth_service

logger = logging.getLogger(__name__)


async def bootstrap_admin() -> None:
    """Create the initial admin user when configured and absent."""
    if not settings.admin_email or not settings.admin_password:
        return

    async with async_session() as db:
        existing = await auth_service.get_user_by_email(settings.admin_email, db)
        if existing is not None:
            return

        await auth_service.create_user(
            email=settings.admin_email,
            password=settings.admin_password,
            role=Role.ADMIN,
            db=db,
        )
        logger.info("Bootstrap admin user created")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """
    Application lifespan handler.

    Runs setup on startup and cleanup on shutdown.
    Database connections, Redis pools, and vector store
    clients will be initialized here in later phases.
    """
    # ── Startup ──────────────────────────────────────────────────────
    logger.info("AI Workspace API starting in %s mode", settings.app_env)
    try:
        await bootstrap_admin()
    except Exception:
        logger.exception("Failed to bootstrap the admin user")
    yield
    # ── Shutdown ─────────────────────────────────────────────────────
    logger.info("AI Workspace API shutting down")


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
app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
app.include_router(users.router, prefix="/api/users", tags=["Users"])
app.include_router(settings_router.router, prefix="/api/settings", tags=["Settings"])
app.include_router(chat.router, prefix="/api/chat", tags=["Chat"])
app.include_router(rag.router, prefix="/api/rag", tags=["RAG"])
app.include_router(agent.router, prefix="/api/agent", tags=["Agent"])
app.include_router(skills.router, prefix="/api/skills", tags=["Skills"])
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
