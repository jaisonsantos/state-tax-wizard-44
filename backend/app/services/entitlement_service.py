"""Entitlement service for plan limits and feature gates."""
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..models.models import OrderFee, Subscription
from ..core.config import settings
from ..observability import (
    enterprise_overage_total,
    entitlement_denials_total,
    entitlement_warnings_total,
    log_billing_event,
)

logger = logging.getLogger(__name__)


class EntitlementService:
    """Service for managing plan entitlements and limits."""
    
    DEFAULT_PLAN = "starter"
    WARN_THRESHOLD_PCT = 80
    WARN_GRACE_ENABLED = True
    ENTERPRISE_OVERAGE_ENABLED = True

    PLAN_LIMITS: Dict[str, Dict[str, Any]] = {
        "free": {
            "display_name": "Free / Dev",
            "monthly_price": 0,
            "annual_price": 0,
            "transactions_per_month": 20,
            "deliveries_included": 20,
            "warn_threshold_pct": WARN_THRESHOLD_PCT,
            "features": ["fee_calculation", "basic_reports"],
            "advanced_reports": False,
            "analytics_dashboard": False,
            "integrations": False,
            "marketing_features": [
                "CO/MN cálculo básico",
                "Dashboard básico",
                "Suporte comunidade",
            ],
            "stripe_price_attr": None,
            "is_enterprise": False,
            "overage_enabled": False,
            "overage_fee": None,
            "commit_deliveries": None,
            "unlimited": False,
        },
        "starter": {
            "display_name": "Starter",
            "monthly_price": 10,
            "annual_price": 100,
            "transactions_per_month": 100,
            "deliveries_included": 100,
            "warn_threshold_pct": WARN_THRESHOLD_PCT,
            "features": ["fee_calculation", "basic_reports", "auto_apply"],
            "advanced_reports": False,
            "analytics_dashboard": False,
            "integrations": False,
            "marketing_features": [
                "Cálculo & aplicação automática",
                "Atualizações automáticas",
                "Relatório mensal",
                "Suporte por e-mail (D+1)",
            ],
            "stripe_price_attr": "stripe_price_id_starter",
            "is_enterprise": False,
            "overage_enabled": False,
            "overage_fee": None,
            "commit_deliveries": None,
            "unlimited": False,
        },
        "pro": {
            "display_name": "Pro",
            "monthly_price": 29,
            "annual_price": 290,
            "transactions_per_month": 1000,
            "deliveries_included": 1000,
            "warn_threshold_pct": WARN_THRESHOLD_PCT,
            "features": [
                "fee_calculation",
                "basic_reports",
                "auto_apply",
                "advanced_reports",
                "analytics_dashboard",
                "webhooks",
            ],
            "advanced_reports": True,
            "analytics_dashboard": True,
            "integrations": False,
            "marketing_features": [
                "Tudo do Starter",
                "CSV avançado",
                "Webhooks/API",
                "Suporte prioritário",
            ],
            "stripe_price_attr": "stripe_price_id_pro",
            "is_enterprise": False,
            "overage_enabled": False,
            "overage_fee": None,
            "commit_deliveries": None,
            "unlimited": False,
        },
        "plus": {
            "display_name": "Plus",
            "monthly_price": 79,
            "annual_price": 790,
            "transactions_per_month": 5000,
            "deliveries_included": 5000,
            "warn_threshold_pct": WARN_THRESHOLD_PCT,
            "features": [
                "fee_calculation",
                "basic_reports",
                "auto_apply",
                "advanced_reports",
                "analytics_dashboard",
                "webhooks",
                "integrations",
            ],
            "advanced_reports": True,
            "analytics_dashboard": True,
            "integrations": True,
            "marketing_features": [
                "Tudo do Pro",
                "Multi-store",
                "Onboarding assistido",
                "SLA",
            ],
            "stripe_price_attr": "stripe_price_id_plus",
            "is_enterprise": False,
            "overage_enabled": False,
            "overage_fee": None,
            "commit_deliveries": None,
            "unlimited": False,
        },
        "enterprise_e10k": {
            "display_name": "Enterprise 10k",
            "monthly_price": 149,
            "annual_price": 149 * 12 * 0.83,
            "transactions_per_month": 10000,
            "deliveries_included": None,
            "commit_deliveries": 10000,
            "warn_threshold_pct": WARN_THRESHOLD_PCT,
            "features": [
                "fee_calculation",
                "advanced_reports",
                "analytics_dashboard",
                "webhooks",
                "integrations",
            ],
            "advanced_reports": True,
            "analytics_dashboard": True,
            "integrations": True,
            "marketing_features": [
                "Tudo do Plus",
                "Commit 10k",
                "Overage monitorado",
            ],
            "stripe_price_attr": "stripe_price_id_e10k",
            "is_enterprise": True,
            "overage_enabled": True,
            "overage_fee": 0.02,
            "unlimited": False,
        },
        "enterprise_e25k": {
            "display_name": "Enterprise 25k",
            "monthly_price": 299,
            "annual_price": 299 * 12 * 0.83,
            "transactions_per_month": 25000,
            "deliveries_included": None,
            "commit_deliveries": 25000,
            "warn_threshold_pct": WARN_THRESHOLD_PCT,
            "features": [
                "fee_calculation",
                "advanced_reports",
                "analytics_dashboard",
                "webhooks",
                "integrations",
            ],
            "advanced_reports": True,
            "analytics_dashboard": True,
            "integrations": True,
            "marketing_features": [
                "Tudo do Plus",
                "Commit 25k",
                "Overage monitorado",
            ],
            "stripe_price_attr": "stripe_price_id_e25k",
            "is_enterprise": True,
            "overage_enabled": True,
            "overage_fee": 0.015,
            "unlimited": False,
        },
        "enterprise_e50k": {
            "display_name": "Enterprise 50k",
            "monthly_price": 499,
            "annual_price": 499 * 12 * 0.83,
            "transactions_per_month": 50000,
            "deliveries_included": None,
            "commit_deliveries": 50000,
            "warn_threshold_pct": WARN_THRESHOLD_PCT,
            "features": [
                "fee_calculation",
                "advanced_reports",
                "analytics_dashboard",
                "webhooks",
                "integrations",
            ],
            "advanced_reports": True,
            "analytics_dashboard": True,
            "integrations": True,
            "marketing_features": [
                "Tudo do Plus",
                "Commit 50k",
                "Overage monitorado",
            ],
            "stripe_price_attr": "stripe_price_id_e50k",
            "is_enterprise": True,
            "overage_enabled": True,
            "overage_fee": 0.01,
            "unlimited": False,
        },
    }

    ENTERPRISE_PLAN_KEYS = {
        "enterprise_e10k",
        "enterprise_e25k",
        "enterprise_e50k",
    }
    
    @staticmethod
    def get_plan_limits(plan_tier: str) -> Dict[str, Any]:
        """Get limits for a plan tier."""

        return EntitlementService.PLAN_LIMITS.get(
            plan_tier,
            EntitlementService.PLAN_LIMITS[EntitlementService.DEFAULT_PLAN],
        )

    @staticmethod
    def get_price_configuration() -> Dict[str, bool]:
        """Return which plan tiers have Stripe price IDs configured."""

        configuration: Dict[str, bool] = {}
        for plan_key, metadata in EntitlementService.PLAN_LIMITS.items():
            price_attr = metadata.get("stripe_price_attr")
            if price_attr:
                configuration[plan_key] = bool(getattr(settings, price_attr, None))
            else:
                configuration[plan_key] = False
        return configuration

    @staticmethod
    def is_enterprise_plan(plan_tier: str) -> bool:
        """Return whether a plan is part of the enterprise catalogue."""

        return plan_tier in EntitlementService.ENTERPRISE_PLAN_KEYS

    @staticmethod
    def plan_exists(plan_tier: str) -> bool:
        """Return whether a plan tier is defined in the pricing catalog."""

        return plan_tier in EntitlementService.PLAN_LIMITS
    
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
            default_plan = EntitlementService.DEFAULT_PLAN
            return Subscription(
                store_id=store_id,
                provider="stripe",
                plan=default_plan,
                plan_tier=default_plan,
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
        warn_threshold = limits.get("warn_threshold_pct", EntitlementService.WARN_THRESHOLD_PCT)

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
        
        usage_pct = (transaction_count / monthly_limit * 100) if monthly_limit else 0.0

        is_enterprise = EntitlementService.is_enterprise_plan(subscription.plan_tier)
        overage_enabled = bool(limits.get("overage_enabled") and EntitlementService.ENTERPRISE_OVERAGE_ENABLED)

        if is_enterprise and overage_enabled:
            if transaction_count > monthly_limit:
                overage_units = transaction_count - monthly_limit
                enterprise_overage_total.labels(plan=subscription.plan_tier).inc()
                log_billing_event(
                    "enterprise_overage_detected",
                    store_id=store_id,
                    plan_tier=subscription.plan_tier,
                    transactions_used=transaction_count,
                    commit=monthly_limit,
                    overage_units=overage_units,
                    overage_fee=limits.get("overage_fee"),
                )
            # Enterprise plans do not block usage; monitoring handles follow-up.
            return

        if transaction_count < monthly_limit:
            return

        if settings.app_env == "dev":
            logger.warning(
                "[DEV] Store %s reached transaction limit: %s/%s (%.2f%%)",
                store_id,
                transaction_count,
                monthly_limit,
                usage_pct,
            )
            return

        logger.warning(
            "Store %s exceeded transaction limit: %s/%s (warn %.0f%%)",
            store_id,
            transaction_count,
            monthly_limit,
            warn_threshold,
        )
        entitlement_denials_total.labels(feature="transactions", plan=subscription.plan_tier).inc()
        log_billing_event(
            "transaction_limit_exceeded",
            store_id=store_id,
            plan_tier=subscription.plan_tier,
            current_usage=transaction_count,
            limit=monthly_limit,
            usage_pct=usage_pct,
        )
        raise HTTPException(
            status_code=403,
            detail={
                "code": "transaction_limit_exceeded",
                "message": f"Monthly transaction limit of {monthly_limit} exceeded. Please upgrade your plan.",
                "current_usage": transaction_count,
                "limit": monthly_limit,
                "percentage_used": usage_pct,
            },
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
        warn_threshold = limits.get("warn_threshold_pct", EntitlementService.WARN_THRESHOLD_PCT)
        unlimited = bool(limits.get("unlimited")) if monthly_limit is None else False
        usage_pct = (transaction_count / monthly_limit * 100) if monthly_limit else 0.0

        warnings: List[str] = []
        if (
            monthly_limit
            and EntitlementService.WARN_GRACE_ENABLED
            and usage_pct >= warn_threshold
        ):
            warning_message = (
                f"{transaction_count} of {monthly_limit} deliveries used ({usage_pct:.1f}% of allocation)."
            )
            warnings.append(warning_message)
            entitlement_warnings_total.labels(plan=subscription.plan_tier).inc()

        enterprise_overage: Optional[Dict[str, Any]] = None
        if EntitlementService.is_enterprise_plan(subscription.plan_tier) and monthly_limit:
            commit = limits.get("commit_deliveries") or monthly_limit
            if transaction_count > commit:
                overage_units = transaction_count - commit
                overage_fee = limits.get("overage_fee")
                enterprise_overage = {
                    "commit_deliveries": commit,
                    "overage_units": overage_units,
                    "overage_fee": overage_fee,
                    "estimated_overage_cost": round(overage_units * (overage_fee or 0), 2)
                    if overage_fee
                    else 0.0,
                }

        usage = {
            "plan": subscription.plan_tier,
            "status": subscription.status,
            "transactions_used": transaction_count,
            "transactions_limit": monthly_limit,
            "unlimited": unlimited,
            "percentage_used": usage_pct,
            "period_start": period_start,
            "period_end": subscription.current_period_end,
            "warn_threshold_pct": warn_threshold,
            "warnings": warnings,
            "enterprise_overage": enterprise_overage,
        }

        log_billing_event(
            "usage_fetched",
            store_id=store_id,
            plan_tier=subscription.plan_tier,
            transactions_used=transaction_count,
            unlimited=usage["unlimited"],
            warnings=len(warnings),
        )

        return usage
