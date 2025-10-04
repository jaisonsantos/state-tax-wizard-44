import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
import stripe

from ..core.config import settings
from ..core.deps import AuthContext, assert_store_access, get_auth_context
from ..db.database import get_db
from ..schema.billing import (
    CheckoutSessionRequest,
    CheckoutSessionResponse,
    Entitlements,
    PortalSessionResponse,
    UsageResponse,
)
from ..services.entitlement_service import EntitlementService
from ..services.stripe_service import StripeCustomerMissingError, StripeService
from ..services.webhook_service import WebhookService
from ..observability import log_billing_event

router = APIRouter(prefix="/v1/billing", tags=["billing"])

logger = logging.getLogger(__name__)

# Configure Stripe (if available)
if settings.stripe_secret_key:
    stripe.api_key = settings.stripe_secret_key


def _ensure_billing_configured() -> None:
    if not settings.stripe_secret_key:
        log_billing_event("billing_unconfigured")
        raise HTTPException(
            status_code=503,
            detail={"code": "billing_unconfigured", "message": "Stripe integration not configured"},
        )


@router.get("/entitlements", response_model=Entitlements)
async def get_entitlements(
    store_id: str = Query(...),
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_auth_context),
):
    """Get billing entitlements for a store with real subscription data."""
    _ensure_billing_configured()
    assert_store_access(db, auth, store_id)

    # Get subscription
    subscription = EntitlementService.get_subscription(db, store_id)
    limits = EntitlementService.get_plan_limits(subscription.plan_tier)

    payload = Entitlements(
        plan=subscription.plan_tier,
        trial_ends_at=subscription.trial_end,
        provider=subscription.provider,
        status=subscription.status,
        current_period_start=getattr(subscription, "current_period_start", None),
        current_period_end=subscription.current_period_end,
        cancel_at_period_end=getattr(subscription, "cancel_at_period_end", False),
        features=list(limits.get("features", [])),
        limits={
            "transactions_per_month": limits.get("transactions_per_month"),
            "advanced_reports": limits.get("advanced_reports", False),
            "analytics_dashboard": limits.get("analytics_dashboard", False),
            "integrations": limits.get("integrations", False),
        },
    )

    log_billing_event(
        "entitlements_requested",
        store_id=store_id,
        plan_tier=subscription.plan_tier,
        status=subscription.status,
    )

    return payload


@router.get("/usage", response_model=UsageResponse)
async def get_usage(
    store_id: str = Query(...),
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_auth_context),
):
    """Get current usage statistics for a store."""
    _ensure_billing_configured()
    assert_store_access(db, auth, store_id)
    
    usage = EntitlementService.get_current_usage(db, store_id)

    response = UsageResponse(**usage)
    log_billing_event(
        "usage_requested",
        store_id=store_id,
        plan_tier=response.plan,
        transactions_used=response.transactions_used,
        unlimited=response.unlimited,
    )

    return response


@router.post("/create-checkout-session", response_model=CheckoutSessionResponse)
async def create_checkout_session(
    request: CheckoutSessionRequest,
    store_id: str = Query(...),
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_auth_context),
):
    """Create Stripe Checkout Session for subscription upgrade."""
    _ensure_billing_configured()
    assert_store_access(db, auth, store_id)

    plan_tier = request.plan_tier.lower()
    price_attr = f"stripe_price_id_{plan_tier}"
    price_id = getattr(settings, price_attr, None)
    if not price_id:
        log_billing_event("price_id_missing", plan_tier=plan_tier)
        raise HTTPException(
            status_code=503,
            detail={
                "code": "billing_unconfigured",
                "message": "Stripe price IDs not configured for checkout",
            },
        )

    result = StripeService.create_checkout_session(
        db=db,
        store_id=store_id,
        price_id=price_id,
        success_url=request.success_url,
        cancel_url=request.cancel_url,
        plan_tier=plan_tier,
    )

    log_billing_event(
        "checkout_session_returned",
        store_id=store_id,
        plan_tier=plan_tier,
        session_id=result.get("session_id"),
    )

    return CheckoutSessionResponse(**{k: result[k] for k in ("session_id", "url")})


@router.post("/create-portal-session", response_model=PortalSessionResponse)
async def create_portal_session(
    store_id: str = Query(...),
    return_url: str = Query(...),
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_auth_context),
):
    """Create Stripe Customer Portal session for subscription management."""
    _ensure_billing_configured()
    assert_store_access(db, auth, store_id)
    
    try:
        session_payload = StripeService.create_portal_session(
            db=db,
            store_id=store_id,
            return_url=return_url,
        )
    except StripeCustomerMissingError:
        log_billing_event("portal_customer_missing", store_id=store_id)
        raise HTTPException(
            status_code=400,
            detail={
                "code": "stripe_customer_missing",
                "message": "Stripe customer not configured for this store",
            },
        )

    log_billing_event(
        "portal_session_returned",
        store_id=store_id,
        portal_session_id=session_payload.get("portal_session_id"),
    )

    return PortalSessionResponse(**session_payload)


@router.post("/webhooks/stripe")
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(None, alias="stripe-signature"),
    db: Session = Depends(get_db),
):
    """Handle Stripe webhook events."""
    if not settings.stripe_webhook_secret:
        raise HTTPException(
            status_code=503,
            detail={"code": "billing_unconfigured", "message": "Webhook secret not configured"},
        )

    if not stripe_signature:
        raise HTTPException(status_code=400, detail="Missing stripe-signature header")

    payload = await request.body()
    
    try:
        # Verify webhook signature
        event = stripe.Webhook.construct_event(
            payload, stripe_signature, settings.stripe_webhook_secret
        )
    except ValueError:
        log_billing_event("webhook_invalid_payload")
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError:
        log_billing_event("webhook_invalid_signature")
        raise HTTPException(status_code=400, detail="Invalid signature")

    result = WebhookService.handle_stripe_event(db, event)

    if result.status_code >= 400:
        raise HTTPException(status_code=result.status_code, detail=result.message)

    log_payload = {
        "event_type": event.get("type"),
        "outcome": result.outcome,
    }
    if result.store_id:
        log_payload["store_id"] = result.store_id
    log_billing_event("webhook_processed", **log_payload)

    response_body = {
        "status": "success" if result.outcome == "processed" and result.generated_event_id else result.outcome,
        "outcome": result.outcome,
        "message": result.message,
        "event_id": event.get("id"),
        "store_id": result.store_id,
    }

    return JSONResponse(status_code=result.status_code, content=response_body)


@router.post("/webhooks/stripe/replay/{event_id}")
async def replay_stripe_webhook(
    event_id: str,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_auth_context),
):
    """Replay a Stripe webhook event that previously failed."""

    result = WebhookService.replay_stripe_event(db, event_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Webhook event not found")

    return JSONResponse(
        status_code=result.status_code,
        content={
            "status": result.outcome,
            "message": result.message,
            "event_id": event_id,
            "store_id": result.store_id,
        },
    )
