"""AI Workspace API — Router Package."""

from app.routers import (
    agent,
    auth,
    chat,
    documents,
    rag,
    settings,
    skills,
    users,
    workspaces,
)

__all__ = [
    "agent",
    "auth",
    "chat",
    "documents",
    "rag",
    "settings",
    "skills",
    "users",
    "workspaces",
]
