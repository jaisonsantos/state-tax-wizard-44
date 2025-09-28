#!/usr/bin/env python3
"""
Seed the database with initial data
"""
from sqlalchemy.orm import sessionmaker
from app.db.database import engine
from app.models.models import Store, StoreSetting, RuleVersion, Subscription
from datetime import datetime, timedelta
import uuid

def seed_database():
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    
    try:
        # Create demo store
        demo_store = Store(
            id=uuid.uuid4(),
            platform="shopify",
            domain="demo-store.myshopify.com",
            country="US",
            state="MN"
        )
        db.add(demo_store)
        db.flush()  # Get the ID
        
        # Create store settings
        store_setting = StoreSetting(
            store_id=demo_store.id,
            enable_mn=True,
            enable_co=True,
            absorb_fee=False,
            label_override="Delivery Fee",
            plan="starter"
        )
        db.add(store_setting)
        
        # Create MN rule version
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
        
        # Create CO rule version
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
        
        # Create demo subscription
        subscription = Subscription(
            store_id=demo_store.id,
            provider="stripe",
            plan="starter",
            status="trialing",
            trial_end=datetime.utcnow() + timedelta(days=14),
            current_period_end=datetime.utcnow() + timedelta(days=30)
        )
        db.add(subscription)
        
        # Create second demo store (WooCommerce)
        woo_store = Store(
            id=uuid.uuid4(),
            platform="woo",
            domain="demo-woo.com",
            country="US",
            state="CO"
        )
        db.add(woo_store)
        db.flush()
        
        woo_setting = StoreSetting(
            store_id=woo_store.id,
            enable_mn=False,
            enable_co=True,
            absorb_fee=False,
            label_override="Colorado Delivery Fee",
            plan="pro"
        )
        db.add(woo_setting)
        
        woo_subscription = Subscription(
            store_id=woo_store.id,
            provider="stripe",
            plan="pro",
            status="active",
            trial_end=None,
            current_period_end=datetime.utcnow() + timedelta(days=30)
        )
        db.add(woo_subscription)
        
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