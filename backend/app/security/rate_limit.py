"""Simple in-memory token/route rate limiter for MVP usage."""
from __future__ import annotations

import threading
import time
from collections import defaultdict, deque
from typing import Deque, DefaultDict, Tuple

from fastapi import HTTPException, status


class RateLimiter:
    """A naive fixed-window rate limiter keyed by (token, route)."""

    def __init__(self, limit: int = 120, window_seconds: int = 60) -> None:
        self.limit = limit
        self.window_seconds = window_seconds
        self._buckets: DefaultDict[Tuple[str, str], Deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def check(self, token: str, route: str) -> None:
        now = time.monotonic()
        key = (token, route)
        with self._lock:
            bucket = self._buckets[key]
            while bucket and now - bucket[0] > self.window_seconds:
                bucket.popleft()
            if len(bucket) >= self.limit:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail={
                        "message": "Rate limit exceeded",
                        "retry_after_seconds": max(
                            1, int(self.window_seconds - (now - bucket[0]))
                        ),
                        "route": route,
                    },
                )
            bucket.append(now)

    def reset(self) -> None:
        """Clear all counters (useful for tests)."""

        with self._lock:
            self._buckets.clear()


rate_limiter = RateLimiter()
