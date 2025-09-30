from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class AnalyticsTrend(str, Enum):
    UP = "up"
    DOWN = "down"
    FLAT = "flat"


class AnalyticsMetricCard(BaseModel):
    """Represents a KPI card rendered on the dashboard."""

    id: str = Field(..., description="Stable identifier for the KPI card")
    title: str = Field(..., description="Display name for the KPI")
    value: float = Field(..., description="Raw numeric value used for charts")
    formatted_value: str = Field(..., description="Pre-formatted display value (e.g., $1,200)")
    delta: float = Field(..., description="Absolute change compared to the previous window")
    delta_percentage: float = Field(..., description="Percentage change compared to the previous window")
    trend: AnalyticsTrend = Field(..., description="Directional trend for the KPI")
    unit: str = Field(..., description="Unit for the metric (count, currency, percent)")
    jurisdiction: Optional[str] = Field(
        default=None,
        description="Jurisdiction (MN/CO) when the KPI is scoped to a single state",
    )
    insight: Optional[str] = Field(
        default=None,
        description="Helper text rendered under the KPI value",
    )


class AnalyticsRecentDecision(BaseModel):
    id: str
    occurred_at: datetime
    order_id: Optional[str]
    jurisdiction: Optional[str]
    amount_cents: Optional[int]
    outcome: Optional[str]
    reason_codes: List[str] = Field(default_factory=list)


class AnalyticsRecentFeed(BaseModel):
    items: List[AnalyticsRecentDecision]
    next_cursor: Optional[str]


class AnalyticsCounterSnapshot(BaseModel):
    fees_applied_total: int
    fees_absorbed_total: int
    report_exports_total: int


class AnalyticsOverviewResponse(BaseModel):
    store_id: str
    generated_at: datetime
    window_start: datetime
    window_end: datetime
    metric_cards: List[AnalyticsMetricCard]
    recent_decisions: AnalyticsRecentFeed
    counters: AnalyticsCounterSnapshot
