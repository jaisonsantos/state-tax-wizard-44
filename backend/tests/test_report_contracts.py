from __future__ import annotations

from datetime import datetime
from pathlib import Path
import uuid

from sqlalchemy.orm import Session

from app.models.models import OrderFee, Store
from app.services.report_service import ReportService

FIXTURES = Path(__file__).parent / "fixtures" / "reports"


def _create_store(db_session: Session):
    store = Store(
        id=uuid.uuid4(),
        name="contract-store",
        platform="shopify",
        domain="contract.example.com",
        country="US",
        state="CO",
    )
    db_session.add(store)
    db_session.commit()
    return store.id


def test_co_dr1786_csv_matches_golden(db_session: Session) -> None:
    store_id = _create_store(db_session)

    co_rows = [
        OrderFee(
            store_id=store_id,
            order_id="CO-001",
            jurisdiction="CO",
            amount_cents=28,
            delivery_method="ship",
            absorbed=False,
            rule_version="CO-contract",
            reason_codes=["CO_HAS_TAXABLE_ITEM"],
            display_name="Retail Delivery Fee (CO)",
            status="applied",
            source_of_remittance="merchant",
            applied_at=datetime(2024, 7, 1, 12, 0, 0),
        ),
        OrderFee(
            store_id=store_id,
            order_id="CO-002",
            jurisdiction="CO",
            amount_cents=28,
            delivery_method="ship",
            absorbed=False,
            rule_version="CO-contract",
            reason_codes=["CO_HAS_TAXABLE_ITEM", "REVERSAL_DELIVERY_CANCELLED"],
            display_name="Retail Delivery Fee (CO)",
            status="reversed",
            reversal_reason="DELIVERY_CANCELLED",
            reversed_at=datetime(2024, 7, 2, 12, 0, 0),
            applied_at=datetime(2024, 7, 2, 12, 0, 0),
        ),
    ]
    db_session.add_all(co_rows)
    db_session.commit()

    output = ReportService.generate_co_dr1786(
        store_id,
        datetime(2024, 7, 1, 0, 0, 0),
        datetime(2024, 7, 3, 0, 0, 0),
        db_session,
    )

    expected = (FIXTURES / "co_dr1786.csv").read_text()
    assert output.content.replace("\r\n", "\n").strip() == expected.replace("\r\n", "\n").strip()


def test_mn_csv_matches_golden(db_session: Session) -> None:
    store_id = _create_store(db_session)

    mn_rows = [
        OrderFee(
            store_id=store_id,
            order_id="MN-001",
            jurisdiction="MN",
            amount_cents=50,
            delivery_method="ship",
            absorbed=False,
            rule_version="MN-contract",
            reason_codes=["MN_THRESHOLD_MET"],
            display_name="Road Improvement and Food Delivery Fee (MN)",
            status="applied",
            applied_at=datetime(2024, 1, 15, 9, 0, 0),
        ),
        OrderFee(
            store_id=store_id,
            order_id="MN-002",
            jurisdiction="MN",
            amount_cents=50,
            delivery_method="ship",
            absorbed=True,
            rule_version="MN-contract",
            reason_codes=["MN_THRESHOLD_MET"],
            display_name="Road Improvement and Food Delivery Fee (MN)",
            status="applied",
            applied_at=datetime(2024, 1, 16, 9, 0, 0),
        ),
        OrderFee(
            store_id=store_id,
            order_id="MN-003",
            jurisdiction="MN",
            amount_cents=50,
            delivery_method="ship",
            absorbed=False,
            rule_version="MN-contract",
            reason_codes=["MN_THRESHOLD_MET", "REVERSAL_DELIVERY_CANCELLED"],
            display_name="Road Improvement and Food Delivery Fee (MN)",
            status="reversed",
            reversal_reason="DELIVERY_CANCELLED",
            reversed_at=datetime(2024, 1, 17, 9, 0, 0),
            applied_at=datetime(2024, 1, 17, 9, 0, 0),
        ),
    ]
    db_session.add_all(mn_rows)
    db_session.commit()

    output = ReportService.generate_mn_summary(
        store_id,
        datetime(2024, 1, 14, 0, 0, 0),
        datetime(2024, 1, 18, 0, 0, 0),
        db_session,
        format="csv",
    )

    expected = (FIXTURES / "mn_summary.csv").read_text()
    assert output.content.replace("\r\n", "\n").strip() == expected.replace("\r\n", "\n").strip()
