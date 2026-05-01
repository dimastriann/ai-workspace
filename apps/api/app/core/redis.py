"""
AI Workspace API — Redis Client

Redis connection for caching and Taskiq task broker.
"""

from redis.asyncio import Redis

from app.config import settings

# ── Redis Client ─────────────────────────────────────────────────────────
redis_client = Redis.from_url(
    settings.redis_url,
    decode_responses=True,
)


async def get_redis() -> Redis:
    """Provide Redis client as a dependency."""
    return redis_client
