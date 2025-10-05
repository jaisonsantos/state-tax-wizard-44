"""Tests for the entitlement service."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Iterable

import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.models import OrderFee, Store, StoreSetting, Subscription
from app.observability import enterprise_overage_total, entitlement_warnings_total
from app.services.entitlement_service import EntitlementService


@pytest.fixture
def demo_store(db_session: Session) -> Store:
    store = Store(
        name="Demo Store",
        platform="woo",
        domain="demo.example.com",
        country="US",
        state="MN",
    )
    db_session.add(store)
    db_session.flush()

    settings = StoreSetting(
        store_id=store.id,
        enable_mn=True,
        enable_co=True,
        absorb_fee=False,
        label_override="Delivery Fee",
        plan="starter",
    )
    db_session.add(settings)
    db_session.commit()
    db_session.refresh(store)
    return store


def test_get_plan_limits() -> None:
    free = EntitlementService.get_plan_limits("free")
    assert free["transactions_per_month"] == 20
    assert free["deliveries_included"] == 20

    starter = EntitlementService.get_plan_limits("starter")
    assert starter["transactions_per_month"] == 100
    assert starter["deliveries_included"] == 100
    assert not starter["advanced_reports"]

    pro = EntitlementService.get_plan_limits("pro")
    assert pro["transactions_per_month"] == 1000
    assert pro["advanced_reports"]

    plus = EntitlementService.get_plan_limits("plus")
    assert plus["transactions_per_month"] == 5000
    assert plus["integrations"]

    enterprise = EntitlementService.get_plan_limits("enterprise_e10k")
    assert enterprise["transactions_per_month"] == 10000
    assert enterprise["overage_fee"] == 0.02


def _create_subscription(
    db: Session,
    store_id: str,
    *,
    plan: str,
    status: str = "active",
    period_days: int = 30,
) -> Subscription:
    now = datetime.now(timezone.utc)
    subscription = Subscription(
        store_id=store_id,
        provider="stripe",
        plan=plan,
        plan_tier=plan,
        status=status,
        trial_end=None,
        current_period_end=now + timedelta(days=period_days),
    )
    db.add(subscription)
    db.commit()
    db.refresh(subscription)
    return subscription


def test_check_entitlement_active_subscription(db_session: Session, demo_store: Store) -> None:
    _create_subscription(db_session, str(demo_store.id), plan="pro", status="active")

    assert EntitlementService.check_entitlement(db_session, str(demo_store.id), "analytics_dashboard")
    assert not EntitlementService.check_entitlement(db_session, str(demo_store.id), "integrations")


def test_check_entitlement_inactive_subscription(db_session: Session, demo_store: Store) -> None:
    _create_subscription(db_session, str(demo_store.id), plan="pro", status="canceled")

    assert not EntitlementService.check_entitlement(db_session, str(demo_store.id), "analytics_dashboard")


def _bulk_insert_fees(db: Session, store_id: str, count: int) -> None:
    base_time = datetime.now(timezone.utc)
    rows: Iterable[OrderFee] = []
    for index in range(count):
        rows.append(
            OrderFee(
                store_id=store_id,
                order_id=f"order-{index}",
                jurisdiction="MN",
                amount_cents=150,
                applied_at=base_time,
                delivery_method="ship",
                rule_version="MN-TEST",
                reason_codes=["test"],
            )
        )
    db.bulk_save_objects(rows)
    db.commit()


@pytest.fixture
def patched_starter_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(
        EntitlementService.PLAN_LIMITS["starter"],
        "transactions_per_month",
        5,
    )
    monkeypatch.setitem(
        EntitlementService.PLAN_LIMITS["starter"],
        "deliveries_included",
        5,
    )


@pytest.fixture
def patched_enterprise_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(
        EntitlementService.PLAN_LIMITS["enterprise_e10k"],
        "transactions_per_month",
        5,
    )
    monkeypatch.setitem(
        EntitlementService.PLAN_LIMITS["enterprise_e10k"],
        "commit_deliveries",
        5,
    )


@pytest.fixture
def prod_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "app_env", "prod", raising=False)


def test_enforce_transaction_limit_within_quota(
    db_session: Session,
    demo_store: Store,
    patched_starter_limit,
    prod_env,
) -> None:
    _create_subscription(db_session, str(demo_store.id), plan="starter")
    _bulk_insert_fees(db_session, str(demo_store.id), count=4)

    EntitlementService.enforce_transaction_limit(db_session, str(demo_store.id))


def test_enforce_transaction_limit_exceeded(
    db_session: Session,
    demo_store: Store,
    patched_starter_limit,
    prod_env,
) -> None:
    _create_subscription(db_session, str(demo_store.id), plan="starter")
    _bulk_insert_fees(db_session, str(demo_store.id), count=5)

    with pytest.raises(HTTPException) as exc_info:
        EntitlementService.enforce_transaction_limit(db_session, str(demo_store.id))

    assert exc_info.value.status_code == 403
    detail = exc_info.value.detail
    assert isinstance(detail, dict)
    assert detail.get("code") == "transaction_limit_exceeded"
    assert detail.get("limit") == 5
    assert detail.get("percentage_used") >= 100


def test_enforce_transaction_limit_unlimited(db_session: Session, demo_store: Store) -> None:
    _create_subscription(db_session, str(demo_store.id), plan="plus")
    _bulk_insert_fees(db_session, str(demo_store.id), count=50)

    EntitlementService.enforce_transaction_limit(db_session, str(demo_store.id))


def test_get_current_usage(db_session: Session, demo_store: Store, patched_starter_limit) -> None:
    _create_subscription(db_session, str(demo_store.id), plan="starter")
    _bulk_insert_fees(db_session, str(demo_store.id), count=2)

    usage = EntitlementService.get_current_usage(db_session, str(demo_store.id))

    assert usage["plan"] == "starter"
    assert usage["status"] in {"active", "trialing"}
    assert usage["transactions_used"] == 2
    assert usage["transactions_limit"] == 5
    assert not usage["unlimited"]
    assert usage["percentage_used"] == 40.0
    assert usage["period_start"] is not None
    assert usage["period_start"].tzinfo is not None
    assert usage["warn_threshold_pct"] == EntitlementService.WARN_THRESHOLD_PCT
    assert usage["warnings"] == []
    assert usage["enterprise_overage"] is None


def test_get_current_usage_emits_warning(
    db_session: Session,
    demo_store: Store,
    patched_starter_limit,
) -> None:
    _create_subscription(db_session, str(demo_store.id), plan="starter")
    _bulk_insert_fees(db_session, str(demo_store.id), count=4)

    metric = entitlement_warnings_total.labels(plan="starter")
    before = metric._value.get()

    usage = EntitlementService.get_current_usage(db_session, str(demo_store.id))

    assert usage["warnings"], "Expected warnings at 80% usage"
    after = metric._value.get()
    assert after == before + 1



def test_enterprise_overage_allows_usage(
    db_session: Session,
    demo_store: Store,
    patched_enterprise_limit,
) -> None:
    _create_subscription(db_session, str(demo_store.id), plan="enterprise_e10k")
    _bulk_insert_fees(db_session, str(demo_store.id), count=6)

    metric = enterprise_overage_total.labels(plan="enterprise_e10k")
    before = metric._value.get()

    usage = EntitlementService.get_current_usage(db_session, str(demo_store.id))
    assert usage["enterprise_overage"] is not None
    assert usage["enterprise_overage"]["overage_units"] == 1

    EntitlementService.enforce_transaction_limit(db_session, str(demo_store.id))

    after = metric._value.get()
    assert after == before + 1

