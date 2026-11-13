"""
AI Workspace API — In-memory Rate Limiting

Single-instance sliding-window limiter. Redis can replace it later.
"""

import time
from collections import defaultdict


class InMemoryRateLimiter:
    """Sliding-window limiter keyed by rule and client."""

    def __init__(self) -> None:
        self._events: dict[str, list[float]] = defaultdict(list)

    def allow(self, key: str, limit: int, window_seconds: int) -> bool:
        now = time.monotonic()
        cutoff = now - window_seconds
        events = [event for event in self._events[key] if event > cutoff]

        if len(events) >= limit:
            self._events[key] = events
            return False

        events.append(now)
        self._events[key] = events
        return True

    def reset(self) -> None:
        self._events.clear()


rate_limiter = InMemoryRateLimiter()
