"""
AI Workspace API — Task Broker (Taskiq)

Manages asynchronous background tasks using Taskiq and Redis.
Used for document ingestion, indexing, and complex agent workflows.
"""

from taskiq import AsyncBroker
from taskiq_redis import ListQueueBroker, RedisAsyncResultBackend

from app.config import settings

# ── Redis Broker ─────────────────────────────────────────────────────────
# Taskiq uses Redis to store and distribute tasks to workers.
broker = ListQueueBroker(
    url=settings.redis_url,
).with_result_backend(
    RedisAsyncResultBackend(redis_url=settings.redis_url)
)

# Optional: Add middleware for logging or performance tracking
# broker.add_middleware(...)
