#!/usr/bin/env python3
"""
Seed the database with initial data
"""
from sqlalchemy.orm import sessionmaker
from app.db.database import engine
from datetime import datetime, timedelta

from app.models.models import (
    AuditLog,
    OrderFee,
    Store,
    StoreSetting,
    Subscription,
    RuleVersion,
)
import uuid


def ensure_store(
    db,
    *,
    name: str,
    platform: str,
    domain: str,
    state: str,
    plan: str,
    enable_mn: bool,
    enable_co: bool,
) -> Store:
    store = db.query(Store).filter(Store.name == name).first()
    if not store:
        store = Store(
            id=uuid.uuid4(),
            name=name,
            platform=platform,
            domain=domain,
            country="US",
            state=state,
        )
        db.add(store)
        db.flush()

    if not store.settings:
        settings = StoreSetting(
            store_id=store.id,
            enable_mn=enable_mn,
            enable_co=enable_co,
            absorb_fee=False,
            label_override="Delivery Fee" if state == "MN" else "Colorado Delivery Fee",
            plan=plan,
        )
        db.add(settings)
    else:
        store.settings.enable_mn = enable_mn
        store.settings.enable_co = enable_co
        store.settings.plan = plan

    if not store.subscriptions:
        subscription = Subscription(
            store_id=store.id,
            provider="stripe",
            plan=plan,
            status="trialing" if plan == "starter" else "active",
            trial_end=datetime.utcnow() + timedelta(days=14) if plan == "starter" else None,
            current_period_end=datetime.utcnow() + timedelta(days=30),
        )
        db.add(subscription)

    return store


def seed_fee_history(db, store: Store, days: int = 30) -> None:
    existing = (
        db.query(OrderFee)
        .filter(OrderFee.store_id == store.id)
        .count()
    )
    if existing >= days:
        return

    now = datetime.utcnow()
    actor = "user:seed-operator@example.com"

    for offset in range(days):
        applied_at = now - timedelta(days=offset)
        jurisdiction = "MN" if offset % 2 == 0 else "CO"
        amount_cents = 50 if jurisdiction == "MN" else 28
        order_id = f"{store.name}-ORDER-{offset:04d}"

        if (
            db.query(OrderFee)
            .filter(OrderFee.store_id == store.id, OrderFee.order_id == order_id)
            .first()
        ):
            continue

        fee = OrderFee(
            id=uuid.uuid4(),
            store_id=store.id,
            order_id=order_id,
            jurisdiction=jurisdiction,
            amount_cents=amount_cents,
            applied_at=applied_at,
            delivery_method="ship",
            absorbed=(offset % 5 == 0),
            rule_version="MN-2024" if jurisdiction == "MN" else "CO-2025H1",
            reason_codes=["MN_THRESHOLD_MET"]
            if jurisdiction == "MN"
            else ["CO_HAS_TAXABLE_ITEM"],
            display_name="Delivery Fee",
            status="applied",
        )
        db.add(fee)

        audit_payload = {
            "store_id": str(store.id),
            "order_id": order_id,
            "status": "applied",
            "lines": [
                {
                    "jurisdiction": jurisdiction,
                    "amount_cents": amount_cents,
                    "reason_codes": fee.reason_codes,
                    "rule_version": fee.rule_version,
                    "absorbed": fee.absorbed,
                }
            ],
        }
        db.add(
            AuditLog(
                id=uuid.uuid4(),
                ts=applied_at,
                actor=actor,
                action="fee_apply",
                payload=audit_payload,
            )
        )

        if offset % 6 == 0:
            fee.status = "reversed"
            fee.reversed_at = applied_at + timedelta(hours=4)
            fee.reversal_reason = "CUSTOMER_REQUEST"

            reversal_payload = {
                "store_id": str(store.id),
                "order_id": order_id,
                "status": "reversed",
                "lines": [
                    {
                        "jurisdiction": jurisdiction,
                        "amount_cents": amount_cents,
                        "reason_codes": fee.reason_codes,
                        "rule_version": fee.rule_version,
                        "absorbed": fee.absorbed,
                    }
                ],
                "reversal_reason": fee.reversal_reason,
            }
            db.add(
                AuditLog(
                    id=uuid.uuid4(),
                    ts=fee.reversed_at,
                    actor=actor,
                    action="fee_reverse",
                    payload=reversal_payload,
                )
            )

    # Seed report export history for the last two weeks
    existing_exports = sum(
        1
        for log in db.query(AuditLog)
        .filter(AuditLog.action == "report_export")
        .all()
        if isinstance(log.payload, dict)
        and log.payload.get("store_id") == str(store.id)
    )
    if existing_exports >= 6:
        return

    for offset in range(0, 14, 2):
        ts = now - timedelta(days=offset)
        for report, fmt in (("mn_summary", "json"), ("co_dr1786", "csv")):
            payload = {
                "store_id": str(store.id),
                "report": report,
                "format": fmt,
                "from_date": (ts - timedelta(days=30)).isoformat(),
                "to_date": ts.isoformat(),
                "row_count": 12,
                "outcome": "success",
                "mime_type": "application/json"
                if fmt == "json"
                else "text/csv",
            }
            db.add(
                AuditLog(
                    id=uuid.uuid4(),
                    ts=ts,
                    actor=actor,
                    action="report_export",
                    payload=payload,
                )
            )


def seed_database():
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    try:
        demo_store = ensure_store(
            db,
            name="store_demo_1",
            platform="shopify",
            domain="demo-store.myshopify.com",
            state="MN",
            plan="starter",
            enable_mn=True,
            enable_co=True,
        )

        woo_store = ensure_store(
            db,
            name="store_demo_2",
            platform="woo",
            domain="demo-woo.com",
            state="CO",
            plan="pro",
            enable_mn=False,
            enable_co=True,
        )

        seed_fee_history(db, demo_store)
        seed_fee_history(db, woo_store)

        # Ensure MN rule version exists
        mn_rule = db.query(RuleVersion).filter(RuleVersion.jurisdiction == "MN").first()
        if not mn_rule:
            mn_rule = RuleVersion(
                jurisdiction="MN",
                version="MN-2024",
                effective_from=datetime(2024, 1, 1),
                effective_to=None,
                params={
                    "threshold_cents": 10000,  # $100.00
                    "fee_cents": 50,  # $0.50
                    "applies_to": ["delivery"],
                    "exemptions": ["pickup", "curbside"]
                }
            )
            db.add(mn_rule)

        # Ensure CO rule version exists
        co_rule = db.query(RuleVersion).filter(RuleVersion.jurisdiction == "CO").first()
        if not co_rule:
            co_rule = RuleVersion(
                jurisdiction="CO",
                version="CO-2025H1",
                effective_from=datetime(2024, 7, 1),
                effective_to=None,
                params={
                    "rate_cents": 28,  # $0.28
                    "applies_to": ["delivery_with_taxable"],
                    "exemptions": ["pickup", "curbside"]
                }
            )
            db.add(co_rule)

        db.commit()
        print("Database seeded successfully!")
        
    except Exception as e:
        db.rollback()
        print(f"Error seeding database: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()
