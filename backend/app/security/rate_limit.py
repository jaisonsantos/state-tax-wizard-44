"""Distributed-friendly rate limiter with Redis fallback to in-memory."""
from __future__ import annotations

import threading
import time
from collections import defaultdict, deque
from typing import Deque, DefaultDict, Optional, Protocol, Tuple

from fastapi import HTTPException, status

try:  # pragma: no cover - optional dependency for tests without Redis
    import redis
    from redis.exceptions import RedisError, ResponseError, WatchError
except ImportError:  # pragma: no cover - redis optional in some environments
    redis = None  # type: ignore
    RedisError = Exception  # type: ignore
    ResponseError = Exception  # type: ignore
    WatchError = Exception  # type: ignore

from ..core.config import settings
from ..observability import log_security_event, rate_limit_throttles_total


class RateLimiterProtocol(Protocol):
    """Contract for rate limiter implementations."""

    limit: int
    window_seconds: int

    def check(self, subject: Optional[str], route: str) -> None:
        """Raise an HTTP 429 if the subject exceeded the rate for a route."""

    def reset(self) -> None:
        """Clear all counters (primarily for tests)."""


def _normalise_subject(subject: Optional[str]) -> str:
    candidate = (subject or "anonymous").strip()
    if not candidate:
        return "anonymous"
    return candidate.replace(" ", "_")


def _raise_throttled(subject: str, route: str, retry_after: int) -> None:
    rate_limit_throttles_total.labels(route=route).inc()
    log_security_event(
        {
            "event": "rate_limit_throttle",
            "subject": subject,
            "route": route,
            "retry_after_seconds": retry_after,
        }
    )
    raise HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail={
            "message": "Rate limit exceeded",
            "retry_after_seconds": retry_after,
            "route": route,
        },
    )


class InMemoryRateLimiter(RateLimiterProtocol):
    """Thread-safe sliding window limiter for local/dev usage."""

    def __init__(self, limit: int, window_seconds: int) -> None:
        self.limit = limit
        self.window_seconds = window_seconds
        self._buckets: DefaultDict[Tuple[str, str], Deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def check(self, subject: Optional[str], route: str) -> None:
        now = time.monotonic()
        actor = _normalise_subject(subject)
        key = (actor, route)
        window_floor = now - self.window_seconds
        with self._lock:
            bucket = self._buckets[key]
            while bucket and bucket[0] < window_floor:
                bucket.popleft()
            if len(bucket) >= self.limit:
                retry_after = max(1, int(self.window_seconds - (now - bucket[0])))
                _raise_throttled(actor, route, retry_after)
            bucket.append(now)

    def reset(self) -> None:
        with self._lock:
            self._buckets.clear()


_RATE_LIMIT_LUA = """
local key = KEYS[1]
local limit = tonumber(ARGV[1])
local now = tonumber(ARGV[2])
local window = tonumber(ARGV[3])
redis.call('ZREMRANGEBYSCORE', key, 0, now - window)
local count = redis.call('ZCARD', key)
if count >= limit then
  local oldest = redis.call('ZRANGE', key, 0, 0, 'WITHSCORES')
  local oldest_score = now
  if oldest and #oldest >= 2 then
    oldest_score = tonumber(oldest[2])
  end
  local retry = math.floor(window - (now - oldest_score))
  if retry < 1 then
    retry = 1
  end
  return {0, retry}
end
redis.call('ZADD', key, now, now)
redis.call('EXPIRE', key, window)
return {1, 0}
"""


class RedisRateLimiter(RateLimiterProtocol):
    """Redis-backed sliding window limiter for distributed deployments."""

    def __init__(
        self,
        client: "redis.Redis",
        limit: int,
        window_seconds: int,
        *,
        prefix: str = "rate-limiter",
    ) -> None:
        self.client = client
        self.limit = limit
        self.window_seconds = window_seconds
        self._prefix = prefix
        try:
            self._script = self.client.register_script(_RATE_LIMIT_LUA)
        except RedisError:  # pragma: no cover - fallback for servers without EVALSHA
            self._script = None

    def _key(self, subject: str, route: str) -> str:
        return f"{self._prefix}:{route}:{subject}"

    def check(self, subject: Optional[str], route: str) -> None:
        actor = _normalise_subject(subject)
        key = self._key(actor, route)
        now = time.time()
        try:
            allowed_flag, retry_after_seconds = self._evaluate(key, now)
        except RedisError:
            log_security_event(
                {
                    "event": "rate_limit_degraded",
                    "route": route,
                    "subject": actor,
                }
            )
            return

        if allowed_flag == 0:
            _raise_throttled(actor, route, max(1, retry_after_seconds))

    def reset(self) -> None:
        pattern = f"{self._prefix}:*"
        for key in self.client.scan_iter(match=pattern):
            self.client.delete(key)

    def _evaluate(self, key: str, now: float) -> tuple[int, int]:
        if self._script is not None:
            try:
                allowed, retry_after = self._script(
                    keys=[key],
                    args=[self.limit, now, self.window_seconds],
                )
                return int(allowed), int(retry_after)
            except ResponseError as exc:
                message = str(exc).lower()
                if "evalsha" not in message and "unknown command" not in message:
                    raise
                # Fall through to the transaction-based fallback when scripts are unavailable.
        return self._fallback_eval(key, now)

    def _fallback_eval(self, key: str, now: float) -> tuple[int, int]:
        window_start = now - self.window_seconds
        with self.client.pipeline(transaction=True) as pipe:
            while True:
                try:
                    pipe.watch(key)
                    pipe.zremrangebyscore(key, 0, window_start)
                    current_count = pipe.zcard(key)
                    oldest_entries = pipe.zrange(key, 0, 0, withscores=True)
                    if current_count >= self.limit:
                        pipe.unwatch()
                        oldest_score = now
                        if oldest_entries:
                            oldest_score = float(oldest_entries[0][1])
                        retry_after = max(1, int(self.window_seconds - (now - oldest_score)))
                        return 0, retry_after

                    pipe.multi()
                    pipe.zadd(key, {str(now): now})
                    pipe.expire(key, self.window_seconds)
                    pipe.execute()
                    return 1, 0
                except WatchError:  # pragma: no cover - rare retry path under contention
                    continue


def _build_rate_limiter() -> RateLimiterProtocol:
    if settings.redis_url and redis is not None:
        client = redis.Redis.from_url(settings.redis_url, decode_responses=False)
        return RedisRateLimiter(
            client,
            settings.rate_limit_limit,
            settings.rate_limit_window_seconds,
        )
    return InMemoryRateLimiter(settings.rate_limit_limit, settings.rate_limit_window_seconds)


rate_limiter: RateLimiterProtocol = _build_rate_limiter()

__all__ = ["rate_limiter", "InMemoryRateLimiter", "RedisRateLimiter", "RateLimiterProtocol"]
