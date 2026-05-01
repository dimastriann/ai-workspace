"""
AI Workspace API — Dependency Injection

FastAPI dependencies for database sessions, auth,
and service instances used across routers.
"""

from app.config import settings


async def get_settings():
    """Provide application settings as a dependency."""
    return settings
