"""Entitlement service for plan limits and feature gates."""
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..models.models import OrderFee, Subscription
from ..observability import entitlement_denials_total, log_billing_event

logger = logging.getLogger(__name__)


class EntitlementService:
    """Service for managing plan entitlements and limits."""
    
    # Plan limits configuration
    PLAN_LIMITS = {
        "starter": {
            "transactions_per_month": 1000,
            "features": ["basic_reports", "fee_calculation"],
            "advanced_reports": False,
            "analytics_dashboard": False,
            "integrations": False
        },
        "pro": {
            "transactions_per_month": 10000,
            "features": ["basic_reports", "advanced_reports", "fee_calculation", "analytics_dashboard"],
            "advanced_reports": True,
            "analytics_dashboard": True,
            "integrations": False
        },
        "plus": {
            "transactions_per_month": None,  # Unlimited
            "features": ["basic_reports", "advanced_reports", "fee_calculation", "analytics_dashboard", "integrations", "priority_support"],
            "advanced_reports": True,
            "analytics_dashboard": True,
            "integrations": True
        }
    }
    
    @staticmethod
    def get_plan_limits(plan_tier: str) -> Dict:
        """Get limits for a plan tier.
        
        Args:
            plan_tier: Plan tier name (starter, pro, plus)
            
        Returns:
            Dict with plan limits
        """
        return EntitlementService.PLAN_LIMITS.get(plan_tier, EntitlementService.PLAN_LIMITS["starter"])
    
    @staticmethod
    def get_subscription(db: Session, store_id: str) -> Subscription:
        """Get active subscription for store.
        
        Args:
            db: Database session
            store_id: Store UUID
            
        Returns:
            Subscription object
        """
        subscription = db.query(Subscription).filter(
            Subscription.store_id == store_id
        ).first()

        if not subscription:
            # Return default trial subscription
            return Subscription(
                store_id=store_id,
                provider="stripe",
                plan="starter",
                plan_tier="starter",
                status="trialing",
                trial_end=datetime.now(timezone.utc),
                current_period_start=datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0),
                current_period_end=datetime.now(timezone.utc) + timedelta(days=14),
                cancel_at_period_end=False,
            )

        return subscription
    
    @staticmethod
    def check_entitlement(db: Session, store_id: str, feature: str) -> bool:
        """Check if store has access to a feature.
        
        Args:
            db: Database session
            store_id: Store UUID
            feature: Feature name to check
            
        Returns:
            True if entitled, False otherwise
        """
        subscription = EntitlementService.get_subscription(db, store_id)
        
        # Check if subscription is active
        if subscription.status not in ["active", "trialing"]:
            entitlement_denials_total.labels(feature=feature, plan=subscription.plan_tier).inc()
            return False

        # Get plan limits
        limits = EntitlementService.get_plan_limits(subscription.plan_tier)

        # Check feature access
        allowed = feature in limits.get("features", [])
        if not allowed:
            entitlement_denials_total.labels(feature=feature, plan=subscription.plan_tier).inc()
        return allowed
    
    @staticmethod
    def enforce_transaction_limit(db: Session, store_id: str):
        """Enforce transaction limit for store's plan.
        
        Args:
            db: Database session
            store_id: Store UUID
            
        Raises:
            HTTPException: If limit exceeded
        """
        subscription = EntitlementService.get_subscription(db, store_id)
        limits = EntitlementService.get_plan_limits(subscription.plan_tier)
        
        # Get transaction limit
        monthly_limit = limits.get("transactions_per_month")
        
        # Unlimited for plus plan
        if monthly_limit is None:
            return

        # Count transactions this billing period
        period_start = getattr(
            subscription,
            "current_period_start",
            None,
        ) or datetime.now(timezone.utc).replace(day=1)

        transaction_count = db.query(func.count(OrderFee.id)).filter(
            OrderFee.store_id == store_id,
            OrderFee.applied_at >= period_start,
        ).scalar()
        
        if transaction_count >= monthly_limit:
            logger.warning(f"Store {store_id} exceeded transaction limit: {transaction_count}/{monthly_limit}")
            entitlement_denials_total.labels(feature="transactions", plan=subscription.plan_tier).inc()
            log_billing_event(
                "transaction_limit_exceeded",
                store_id=store_id,
                plan_tier=subscription.plan_tier,
                current_usage=transaction_count,
                limit=monthly_limit,
            )
            raise HTTPException(
                status_code=403,
                detail={
                    "code": "transaction_limit_exceeded",
                    "message": f"Monthly transaction limit of {monthly_limit} exceeded. Please upgrade your plan.",
                    "current_usage": transaction_count,
                    "limit": monthly_limit
                }
            )
    
    @staticmethod
    def get_current_usage(db: Session, store_id: str) -> Dict:
        """Get current usage stats for store.
        
        Args:
            db: Database session
            store_id: Store UUID
            
        Returns:
            Dict with usage information
        """
        subscription = EntitlementService.get_subscription(db, store_id)
        limits = EntitlementService.get_plan_limits(subscription.plan_tier)
        
        # Get transaction count for current period
        period_start = getattr(
            subscription,
            "current_period_start",
            None,
        ) or datetime.now(timezone.utc).replace(day=1)

        transaction_count = db.query(func.count(OrderFee.id)).filter(
            OrderFee.store_id == store_id,
            OrderFee.applied_at >= period_start,
        ).scalar()
        
        monthly_limit = limits.get("transactions_per_month")
        
        usage = {
            "plan": subscription.plan_tier,
            "transactions_used": transaction_count,
            "transactions_limit": monthly_limit,
            "unlimited": monthly_limit is None,
            "percentage_used": (transaction_count / monthly_limit * 100) if monthly_limit else 0.0,
            "period_start": period_start,
            "period_end": subscription.current_period_end,
            "status": subscription.status,
        }

        log_billing_event(
            "usage_fetched",
            store_id=store_id,
            plan_tier=subscription.plan_tier,
            transactions_used=transaction_count,
            unlimited=usage["unlimited"],
        )

        return usage
