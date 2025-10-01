from __future__ import annotations

import pytest
from fastapi import HTTPException

import fakeredis

from app.observability import rate_limit_throttles_total
from app.security.rate_limit import InMemoryRateLimiter, RedisRateLimiter


def test_in_memory_rate_limiter_throttles_subject_route() -> None:
    limiter = InMemoryRateLimiter(limit=2, window_seconds=60)
    limiter.reset()
    metric = rate_limit_throttles_total.labels(route="apply")
    baseline = metric._value.get()

    limiter.check("store-123", "apply")
    limiter.check("store-123", "apply")

    with pytest.raises(HTTPException) as exc:
        limiter.check("store-123", "apply")

    assert exc.value.status_code == 429
    assert metric._value.get() == baseline + 1


def test_redis_rate_limiter_uses_shared_storage() -> None:
    fake = fakeredis.FakeRedis()
    limiter = RedisRateLimiter(fake, limit=1, window_seconds=60)
    limiter.reset()
    metric = rate_limit_throttles_total.labels(route="quote")
    baseline = metric._value.get()

    limiter.check("tenant-1", "quote")

    with pytest.raises(HTTPException) as exc:
        limiter.check("tenant-1", "quote")

    assert exc.value.status_code == 429
    assert metric._value.get() == baseline + 1

    # Ensure the sliding window is per subject/route combination.
    limiter.check("other-tenant", "quote")
