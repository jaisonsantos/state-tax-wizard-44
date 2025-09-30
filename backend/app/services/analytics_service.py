from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Iterable, List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from ..models.models import AuditLog, OrderFee
from ..schema.analytics import (
    AnalyticsCounterSnapshot,
    AnalyticsMetricCard,
    AnalyticsOverviewResponse,
    AnalyticsRecentDecision,
    AnalyticsRecentFeed,
    AnalyticsTrend,
)
from .audit_repository import AuditLogRepository


@dataclass
class FeeSummary:
    applied: int
    absorbed: int
    co_total_cents: int
    mn_total_cents: int
    mn_threshold_met: int


class AnalyticsService:
    """Provides aggregate telemetry for the dashboard."""

    def __init__(self, db: Session):
        self.db = db
        self.audit_repo = AuditLogRepository(db)

    def _fees_between(self, store_id: str, start: datetime, end: datetime) -> List[OrderFee]:
        return (
            self.db.query(OrderFee)
            .filter(
                OrderFee.store_id == store_id,
                OrderFee.applied_at >= start,
                OrderFee.applied_at <= end,
            )
            .all()
        )

    @staticmethod
    def _summarize_fees(fees: Iterable[OrderFee]) -> FeeSummary:
        applied = 0
        absorbed = 0
        co_total = 0
        mn_total = 0
        threshold_met = 0

        for fee in fees:
            if fee.status != "applied":
                continue
            applied += 1
            if fee.absorbed:
                absorbed += 1
            if fee.jurisdiction == "CO":
                co_total += fee.amount_cents
            if fee.jurisdiction == "MN":
                mn_total += fee.amount_cents
                reasons = list(fee.reason_codes or [])
                if any(reason.startswith("MN_THRESHOLD") for reason in reasons):
                    threshold_met += 1

        return FeeSummary(
            applied=applied,
            absorbed=absorbed,
            co_total_cents=co_total,
            mn_total_cents=mn_total,
            mn_threshold_met=threshold_met,
        )

    def _count_reversals(
        self, store_id: str, start: datetime, end: datetime
    ) -> int:
        return (
            self.db.query(func.count(AuditLog.id))
            .filter(
                self.audit_repo.store_filter(store_id),
                AuditLog.action == "fee_reverse",
                AuditLog.ts >= start,
                AuditLog.ts <= end,
            )
            .scalar()
            or 0
        )

    @staticmethod
    def _format_currency(amount_cents: int) -> str:
        dollars = amount_cents / 100
        return f"${dollars:,.2f}"

    @staticmethod
    def _format_percent(value: float) -> str:
        return f"{value * 100:.1f}%"

    @staticmethod
    def _format_number(value: int) -> str:
        return f"{value:,}"

    @staticmethod
    def _delta(current: float, previous: float) -> tuple[float, float, AnalyticsTrend]:
        delta = current - previous
        pct = 0.0 if previous == 0 else delta / previous
        if delta > 0:
            trend = AnalyticsTrend.UP
        elif delta < 0:
            trend = AnalyticsTrend.DOWN
        else:
            trend = AnalyticsTrend.FLAT
        return delta, pct, trend

    def overview(
        self,
        *,
        store_id: str,
        cursor: Optional[str],
        limit: int,
        window_days: int,
        counters: AnalyticsCounterSnapshot,
    ) -> AnalyticsOverviewResponse:
        now = datetime.now(timezone.utc)
        window_end = now
        window_start = now - timedelta(days=window_days)
        previous_start = window_start - timedelta(days=window_days)
        previous_end = window_start

        current_fees = self._fees_between(store_id, window_start, window_end)
        previous_fees = self._fees_between(store_id, previous_start, previous_end)

        current_summary = self._summarize_fees(current_fees)
        previous_summary = self._summarize_fees(previous_fees)

        mn_threshold_rate = (
            0.0
            if current_summary.applied == 0
            else current_summary.mn_threshold_met / current_summary.applied
        )
        previous_threshold_rate = (
            0.0
            if previous_summary.applied == 0
            else previous_summary.mn_threshold_met / previous_summary.applied
        )

        # Exceptions measured via fee reversal audits over 7-day windows
        exceptions_window_days = 7
        current_exceptions = self._count_reversals(
            store_id,
            now - timedelta(days=exceptions_window_days),
            now,
        )
        previous_exceptions = self._count_reversals(
            store_id,
            now - timedelta(days=exceptions_window_days * 2),
            now - timedelta(days=exceptions_window_days),
        )

        metric_cards: List[AnalyticsMetricCard] = []

        delta, pct, trend = self._delta(
            current_summary.applied, previous_summary.applied
        )
        metric_cards.append(
            AnalyticsMetricCard(
                id="fees_applied_30d",
                title="Fees Applied (30d)",
                value=float(current_summary.applied),
                formatted_value=self._format_number(current_summary.applied),
                delta=float(delta),
                delta_percentage=pct,
                trend=trend,
                unit="count",
                insight="Total successful fee applications across all jurisdictions.",
            )
        )

        current_absorb_rate = (
            0.0
            if current_summary.applied == 0
            else current_summary.absorbed / current_summary.applied
        )
        previous_absorb_rate = (
            0.0
            if previous_summary.applied == 0
            else previous_summary.absorbed / previous_summary.applied
        )
        delta, pct, trend = self._delta(current_absorb_rate, previous_absorb_rate)
        metric_cards.append(
            AnalyticsMetricCard(
                id="absorbed_rate_30d",
                title="Fees Absorbed",
                value=current_absorb_rate,
                formatted_value=self._format_percent(current_absorb_rate),
                delta=delta,
                delta_percentage=pct,
                trend=trend,
                unit="percent",
                insight="Share of orders where the merchant absorbed the fee.",
            )
        )

        delta, pct, trend = self._delta(
            current_summary.co_total_cents, previous_summary.co_total_cents
        )
        metric_cards.append(
            AnalyticsMetricCard(
                id="co_fee_total",
                title="CO Fees Total",
                value=float(current_summary.co_total_cents),
                formatted_value=self._format_currency(current_summary.co_total_cents),
                delta=float(delta),
                delta_percentage=pct,
                trend=trend,
                unit="currency_cents",
                jurisdiction="CO",
                insight="Gross Colorado fees collected in the last 30 days.",
            )
        )

        delta, pct, trend = self._delta(
            current_exceptions, previous_exceptions
        )
        metric_cards.append(
            AnalyticsMetricCard(
                id="exceptions_7d",
                title="Exceptions (7d)",
                value=float(current_exceptions),
                formatted_value=self._format_number(current_exceptions),
                delta=float(delta),
                delta_percentage=pct,
                trend=trend,
                unit="count",
                insight="Fee reversals captured in the last 7 days.",
            )
        )

        # Include Minnesota trend insight with helper text referencing docs
        delta, pct, trend = self._delta(mn_threshold_rate, previous_threshold_rate)
        metric_cards.append(
            AnalyticsMetricCard(
                id="mn_threshold_rate",
                title="MN Threshold Met",
                value=mn_threshold_rate,
                formatted_value=self._format_percent(mn_threshold_rate),
                delta=delta,
                delta_percentage=pct,
                trend=trend,
                unit="percent",
                jurisdiction="MN",
                insight="Orders exceeding Minnesota delivery threshold",
            )
        )

        decisions, next_cursor = self.audit_repo.fetch(
            store_id=store_id,
            actions=["fee_apply", "fee_reverse"],
            limit=limit,
            cursor=cursor,
        )

        feed_items: List[AnalyticsRecentDecision] = []
        for log in decisions:
            payload = log.payload if isinstance(log.payload, dict) else {}
            line = None
            if isinstance(payload.get("lines"), list) and payload["lines"]:
                candidate = payload["lines"][0]
                if isinstance(candidate, dict):
                    line = candidate

            feed_items.append(
                AnalyticsRecentDecision(
                    id=str(log.id),
                    occurred_at=log.ts,
                    order_id=payload.get("order_id"),
                    jurisdiction=(line or {}).get("jurisdiction")
                    or payload.get("jurisdiction"),
                    amount_cents=(line or {}).get("amount_cents"),
                    outcome=payload.get("status"),
                    reason_codes=(line or {}).get("reason_codes", []),
                )
            )

        recent_feed = AnalyticsRecentFeed(items=feed_items, next_cursor=next_cursor)

        return AnalyticsOverviewResponse(
            store_id=store_id,
            generated_at=now,
            window_start=window_start,
            window_end=window_end,
            metric_cards=metric_cards,
            recent_decisions=recent_feed,
            counters=counters,
        )
