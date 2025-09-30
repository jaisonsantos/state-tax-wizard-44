from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List

from sqlalchemy.orm import Session

from ..models.models import OrderFee, Store
from ..observability import log_report_event, report_exports_total


@dataclass
class ReportExportResult:
    """Represents a generated report export payload."""

    report: str
    jurisdiction: str
    format: str
    content: str | Dict[str, Any]
    row_count: int


class ReportService:

    @staticmethod
    def generate_co_dr1786(
        store_id: str, from_date: datetime, to_date: datetime, db: Session
    ) -> ReportExportResult:
        """Generate Colorado DR-1786 CSV report"""

        # Query order fees for Colorado
        fees = db.query(OrderFee).join(Store).filter(
            OrderFee.store_id == store_id,
            OrderFee.jurisdiction == "CO",
            OrderFee.applied_at >= from_date,
            OrderFee.applied_at <= to_date,
        ).all()

        # Create CSV content
        output = io.StringIO()
        writer = csv.writer(output)

        # DR-1786 Headers (simplified)
        writer.writerow([
            "Transaction Date",
            "Order ID",
            "Fee Amount",
            "Delivery Method",
            "Reason Codes",
        ])

        for fee in fees:
            amount_cents = fee.amount_cents
            reasons = list(fee.reason_codes or [])
            if fee.status == "reversed":
                amount_cents = -amount_cents
                if fee.reversal_reason:
                    tag = f"REVERSAL_{fee.reversal_reason}"
                    if tag not in reasons:
                        reasons.append(tag)
            writer.writerow([
                fee.applied_at.strftime("%Y-%m-%d"),
                fee.order_id,
                f"${amount_cents / 100:.2f}",
                fee.delivery_method,
                ",".join(reasons),
            ])

        # Add demo data if no real data
        if not fees:
            writer.writerow([
                "2024-01-15",
                "CO-DEMO-001",
                "$0.28",
                "ship",
                "CO_HAS_TAXABLE_ITEM",
            ])
            writer.writerow([
                "2024-01-16",
                "CO-DEMO-002",
                "$0.28",
                "ship",
                "CO_HAS_TAXABLE_ITEM",
            ])

        content = output.getvalue()

        ReportService.observe_export(
            report="co_dr1786",
            jurisdiction="CO",
            store_id=store_id,
            fmt="csv",
            from_date=from_date,
            to_date=to_date,
            row_count=len(fees),
            outcome="success",
        )

        return ReportExportResult(
            report="co_dr1786",
            jurisdiction="CO",
            format="csv",
            content=content,
            row_count=len(fees),
        )

    @staticmethod
    def generate_mn_summary(
        store_id: str,
        from_date: datetime,
        to_date: datetime,
        db: Session,
        format: str = "csv",
    ) -> ReportExportResult:
        """Generate Minnesota Summary report"""

        # Query order fees for Minnesota
        fees: List[OrderFee] = db.query(OrderFee).join(Store).filter(
            OrderFee.store_id == store_id,
            OrderFee.jurisdiction == "MN",
            OrderFee.applied_at >= from_date,
            OrderFee.applied_at <= to_date,
        ).all()

        if format == "csv":
            output = io.StringIO()
            writer = csv.writer(output)

            writer.writerow([
                "Transaction Date",
                "Order ID",
                "Fee Amount",
                "Delivery Method",
                "Reason Codes",
            ])

            for fee in fees:
                amount_cents = fee.amount_cents
                reasons = list(fee.reason_codes or [])
                if fee.status == "reversed":
                    amount_cents = -amount_cents
                    if fee.reversal_reason:
                        tag = f"REVERSAL_{fee.reversal_reason}"
                        if tag not in reasons:
                            reasons.append(tag)
                writer.writerow([
                    fee.applied_at.strftime("%Y-%m-%d"),
                    fee.order_id,
                    f"${amount_cents / 100:.2f}",
                    fee.delivery_method,
                    ",".join(reasons),
                ])

            # Add demo data if no real data
            if not fees:
                writer.writerow([
                    "2024-01-15",
                    "MN-DEMO-001",
                    "$0.50",
                    "ship",
                    "MN_THRESHOLD_MET",
                ])
                writer.writerow([
                    "2024-01-16",
                    "MN-DEMO-002",
                    "$0.50",
                    "ship",
                    "MN_THRESHOLD_MET",
                ])

            content = output.getvalue()

            ReportService.observe_export(
                report="mn_summary",
                jurisdiction="MN",
                store_id=store_id,
                fmt="csv",
                from_date=from_date,
                to_date=to_date,
                row_count=len(fees),
                outcome="success",
            )

            return ReportExportResult(
                report="mn_summary",
                jurisdiction="MN",
                format="csv",
                content=content,
                row_count=len(fees),
            )

        # JSON format for MN summary
        applied_fees = [fee for fee in fees if fee.status == "applied"]
        reversed_fees = [fee for fee in fees if fee.status == "reversed"]

        fee_total_cents = sum(fee.amount_cents for fee in applied_fees) - sum(
            fee.amount_cents for fee in reversed_fees
        )
        absorbed_count = sum(1 for fee in applied_fees if getattr(fee, "absorbed", False)) - sum(
            1 for fee in reversed_fees if getattr(fee, "absorbed", False)
        )
        shown_count = (len(applied_fees) - absorbed_count) - (
            sum(1 for fee in reversed_fees if not getattr(fee, "absorbed", False))
        )

        content = {
            "tx_count_threshold_met": max(len(applied_fees) - len(reversed_fees), 0),
            "fee_total_cents": fee_total_cents,
            "absorbed_count": max(absorbed_count, 0),
            "shown_count": max(shown_count, 0),
        }

        ReportService.observe_export(
            report="mn_summary",
            jurisdiction="MN",
            store_id=store_id,
            fmt="json",
            from_date=from_date,
            to_date=to_date,
            row_count=len(fees),
            outcome="success",
        )

        return ReportExportResult(
            report="mn_summary",
            jurisdiction="MN",
            format="json",
            content=content,
            row_count=len(fees),
        )

    @staticmethod
    def observe_export(
        *,
        report: str,
        jurisdiction: str,
        store_id: str,
        fmt: str,
        from_date: datetime,
        to_date: datetime,
        row_count: int,
        outcome: str,
        error: str | None = None,
    ) -> None:
        """Emit observability signals for report exports."""

        event = {
            "event": "report_export",
            "report": report,
            "jurisdiction": jurisdiction,
            "store_id": store_id,
            "format": fmt,
            "from_date": from_date.isoformat(),
            "to_date": to_date.isoformat(),
            "row_count": row_count,
            "outcome": outcome,
        }
        if error:
            event["error"] = error

        log_report_event(event)

        if outcome == "success":
            report_exports_total.labels(jurisdiction=jurisdiction, format=fmt).inc()
