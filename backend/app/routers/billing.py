from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from sqlalchemy.orm import Session
import stripe

from ..core.config import settings
from ..core.deps import AuthContext, assert_store_access, get_auth_context
from ..db.database import get_db
from ..models.models import Subscription
from ..schema.billing import (
    CheckoutSessionRequest,
    CheckoutSessionResponse,
    Entitlements,
    PortalSessionResponse,
    UsageResponse,
)
from ..services.entitlement_service import EntitlementService
from ..services.stripe_service import StripeService
from ..services.webhook_service import WebhookService

router = APIRouter(prefix="/v1/billing", tags=["billing"])

# Configure Stripe (if available)
if settings.stripe_secret_key:
    stripe.api_key = settings.stripe_secret_key


@router.get("/entitlements", response_model=Entitlements)
async def get_entitlements(
    store_id: str = Query(...),
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_auth_context),
):
    """Get billing entitlements for a store with real subscription data."""
    if not settings.stripe_secret_key:
        raise HTTPException(
            status_code=503,
            detail={"code": "billing_unconfigured", "message": "Stripe integration not configured"}
        )
    
    assert_store_access(db, auth, store_id)

    # Get subscription
    subscription = EntitlementService.get_subscription(db, store_id)
    limits = EntitlementService.get_plan_limits(subscription.plan_tier)

    return Entitlements(
        plan=subscription.plan_tier,
        trial_ends_at=subscription.trial_end,
        provider=subscription.provider,
        status=subscription.status,
        current_period_end=subscription.current_period_end,
        cancel_at_period_end=getattr(subscription, "cancel_at_period_end", False),
        features=limits.get("features", []),
        limits={
            "transactions_per_month": limits.get("transactions_per_month"),
            "advanced_reports": limits.get("advanced_reports", False),
            "analytics_dashboard": limits.get("analytics_dashboard", False),
            "integrations": limits.get("integrations", False),
        },
    )


@router.get("/usage", response_model=UsageResponse)
async def get_usage(
    store_id: str = Query(...),
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_auth_context),
):
    """Get current usage statistics for a store."""
    if not settings.stripe_secret_key:
        raise HTTPException(
            status_code=503,
            detail={"code": "billing_unconfigured", "message": "Stripe integration not configured"}
        )
    
    assert_store_access(db, auth, store_id)
    
    usage = EntitlementService.get_current_usage(db, store_id)
    return UsageResponse(**usage)


@router.post("/create-checkout-session", response_model=CheckoutSessionResponse)
async def create_checkout_session(
    request: CheckoutSessionRequest,
    store_id: str = Query(...),
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_auth_context),
):
    """Create Stripe Checkout Session for subscription upgrade."""
    if not settings.stripe_secret_key:
        raise HTTPException(
            status_code=503,
            detail={"code": "billing_unconfigured", "message": "Stripe integration not configured"}
        )
    
    assert_store_access(db, auth, store_id)
    
    # Map plan tier to Stripe Price ID (these should be in env vars)
    price_ids = {
        "starter": settings.stripe_price_id_starter if hasattr(settings, "stripe_price_id_starter") else "price_starter",
        "pro": settings.stripe_price_id_pro if hasattr(settings, "stripe_price_id_pro") else "price_pro",
        "plus": settings.stripe_price_id_plus if hasattr(settings, "stripe_price_id_plus") else "price_plus",
    }
    
    price_id = price_ids.get(request.plan_tier)
    if not price_id:
        raise HTTPException(status_code=400, detail="Invalid plan tier")
    
    result = StripeService.create_checkout_session(
        db=db,
        store_id=store_id,
        price_id=price_id,
        success_url=request.success_url,
        cancel_url=request.cancel_url,
    )
    
    return CheckoutSessionResponse(**result)


@router.post("/create-portal-session", response_model=PortalSessionResponse)
async def create_portal_session(
    store_id: str = Query(...),
    return_url: str = Query(...),
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_auth_context),
):
    """Create Stripe Customer Portal session for subscription management."""
    if not settings.stripe_secret_key:
        raise HTTPException(
            status_code=503,
            detail={"code": "billing_unconfigured", "message": "Stripe integration not configured"}
        )
    
    assert_store_access(db, auth, store_id)
    
    portal_url = StripeService.create_portal_session(
        db=db,
        store_id=store_id,
        return_url=return_url,
    )
    
    return PortalSessionResponse(portal_url=portal_url)


@router.post("/webhooks/stripe")
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(None, alias="stripe-signature"),
    db: Session = Depends(get_db),
):
    """Handle Stripe webhook events."""
    if not settings.stripe_webhook_secret:
        raise HTTPException(status_code=503, detail="Webhook secret not configured")
    
    if not stripe_signature:
        raise HTTPException(status_code=400, detail="Missing stripe-signature header")
    
    payload = await request.body()
    
    try:
        # Verify webhook signature
        event = stripe.Webhook.construct_event(
            payload, stripe_signature, settings.stripe_webhook_secret
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")
    
    # Handle different event types
    event_type = event["type"]
    
    try:
        if event_type == "customer.subscription.created":
            WebhookService.process_subscription_created(db, event)
        elif event_type == "customer.subscription.updated":
            WebhookService.process_subscription_updated(db, event)
        elif event_type == "customer.subscription.deleted":
            WebhookService.process_subscription_deleted(db, event)
        elif event_type == "invoice.paid":
            WebhookService.process_invoice_paid(db, event)
        elif event_type == "invoice.payment_failed":
            WebhookService.process_invoice_payment_failed(db, event)
    except Exception as e:
        # Log error but return 200 to acknowledge receipt
        print(f"Error processing webhook: {e}")
    
    return {"status": "success"}
