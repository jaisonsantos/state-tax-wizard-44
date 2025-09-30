from __future__ import annotations

import time
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from ..core.deps import AuthContext, assert_store_access, get_auth_context
from ..db.database import get_db
from ..observability import (
    analytics_dashboard_loaded_total,
    ensure_request_id,
    fees_absorbed_total,
    fees_applied_total,
    log_analytics_event,
    report_exports_total,
)
from ..schema.analytics import AnalyticsCounterSnapshot, AnalyticsOverviewResponse
from ..services.analytics_service import AnalyticsService

router = APIRouter(prefix="/v1/analytics", tags=["analytics"])


def _sum_counter(counter) -> int:
    total = 0
    for metric in counter.collect():
        for sample in metric.samples:
            if sample.name.endswith("_total"):
                total += int(sample.value)
    return total


def get_counter_snapshot() -> AnalyticsCounterSnapshot:
    return AnalyticsCounterSnapshot(
        fees_applied_total=_sum_counter(fees_applied_total),
        fees_absorbed_total=_sum_counter(fees_absorbed_total),
        report_exports_total=_sum_counter(report_exports_total),
    )


@router.get("/overview", response_model=AnalyticsOverviewResponse)
async def get_analytics_overview(
    request: Request,
    store_id: str = Query(..., description="Store identifier to scope analytics"),
    limit: int = Query(10, ge=1, le=50),
    cursor: Optional[str] = Query(default=None, description="Pagination cursor"),
    window_days: int = Query(30, ge=7, le=90),
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_auth_context),
    counters: AnalyticsCounterSnapshot = Depends(get_counter_snapshot),
) -> AnalyticsOverviewResponse:
    assert_store_access(db, auth, store_id)

    service = AnalyticsService(db)
    start = time.perf_counter()
    overview = service.overview(
        store_id=store_id,
        cursor=cursor,
        limit=limit,
        window_days=window_days,
        counters=counters,
    )
    duration_ms = (time.perf_counter() - start) * 1000

    request_id = ensure_request_id(request.headers.get("x-request-id"))
    analytics_dashboard_loaded_total.labels(store_id=store_id).inc()
    log_analytics_event(
        {
            "event": "analytics_dashboard_loaded",
            "store_id": store_id,
            "metric_cards": len(overview.metric_cards),
            "feed_length": len(overview.recent_decisions.items),
            "next_cursor": overview.recent_decisions.next_cursor,
            "duration_ms": round(duration_ms, 2),
            "request_id": request_id,
        }
    )

    return overview
