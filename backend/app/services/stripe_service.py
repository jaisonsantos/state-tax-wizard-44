"""Stripe service for customer and subscription management."""
import logging
from datetime import datetime, timezone
from typing import Optional

import stripe
from sqlalchemy.orm import Session, joinedload

from ..core.config import settings
from ..models.models import Store, Subscription
from ..observability import checkout_sessions_created_total, log_billing_event

logger = logging.getLogger(__name__)

def _ensure_api_key() -> None:
    """Ensure Stripe is configured before making API calls."""

    if not settings.stripe_secret_key:
        raise RuntimeError("Stripe integration not configured")
    if stripe.api_key != settings.stripe_secret_key:
        stripe.api_key = settings.stripe_secret_key


class StripeCustomerMissingError(RuntimeError):
    """Raised when a store lacks the Stripe metadata required for portal access."""


class StripeService:
    """Service for managing Stripe customers and subscriptions."""
    
    @staticmethod
    def _resolve_contact_email(store: Store) -> str:
        """Determine the best contact email for a store."""

        if store.contact_email:
            return store.contact_email

        for user in getattr(store, "users", []) or []:
            email = getattr(user, "email", None)
            if email:
                return email

        # Fallback to a deterministic placeholder to avoid None values.
        return f"billing+{store.id}@example.com"

    @staticmethod
    def create_customer(
        db: Session,
        store_id: str,
        email: str,
        name: str
    ) -> str:
        """Create a Stripe customer and link to store.
        
        Args:
            db: Database session
            store_id: Store UUID
            email: Customer email
            name: Customer name
            
        Returns:
            Stripe customer ID
        """
        try:
            # Create Stripe customer
            customer = stripe.Customer.create(
                email=email,
                name=name,
                metadata={"store_id": store_id}
            )
            
            # Update store with customer ID
            store = db.query(Store).filter(Store.id == store_id).first()
            if store:
                store.stripe_customer_id = customer.id
                if email and store.contact_email != email:
                    store.contact_email = email
                db.commit()

            logger.info(f"Created Stripe customer {customer.id} for store {store_id}")
            return customer.id
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error creating customer: {e}")
            raise
    
    @staticmethod
    def get_or_create_customer(
        db: Session,
        store_id: str,
        email: str,
        name: str,
        store: Optional[Store] = None,
    ) -> str:
        """Get existing Stripe customer or create new one.
        
        Args:
            db: Database session
            store_id: Store UUID
            email: Customer email
            name: Customer name
            
        Returns:
            Stripe customer ID
        """
        store_obj = store or db.query(Store).filter(Store.id == store_id).first()

        if store_obj and store_obj.stripe_customer_id:
            if email and store_obj.contact_email != email:
                store_obj.contact_email = email
                db.commit()
            return store_obj.stripe_customer_id

        return StripeService.create_customer(db, store_id, email, name)
    
    @staticmethod
    def create_checkout_session(
        db: Session,
        store_id: str,
        price_id: str,
        success_url: str,
        cancel_url: str,
        plan_tier: str,
    ) -> dict:
        """Create Stripe Checkout Session for subscription.
        
        Args:
            db: Database session
            store_id: Store UUID
            price_id: Stripe Price ID
            success_url: URL to redirect on success
            cancel_url: URL to redirect on cancel
            
        Returns:
            Dict with session_id and checkout_url
        """
        try:
            _ensure_api_key()
            store = (
                db.query(Store)
                .options(joinedload(Store.users))
                .filter(Store.id == store_id)
                .first()
            )
            if not store:
                raise ValueError(f"Store {store_id} not found")

            # Get or create customer
            contact_email = StripeService._resolve_contact_email(store)
            customer_id = StripeService.get_or_create_customer(
                db,
                store_id,
                contact_email,
                store.name,
                store=store,
            )
            
            # Create checkout session
            session = stripe.checkout.Session.create(
                customer=customer_id,
                payment_method_types=["card"],
                line_items=[{
                    "price": price_id,
                    "quantity": 1
                }],
                mode="subscription",
                success_url=success_url,
                cancel_url=cancel_url,
                metadata={"store_id": store_id}
            )
            
            checkout_sessions_created_total.labels(plan_tier=plan_tier).inc()
            log_billing_event(
                "checkout_session_created",
                store_id=store_id,
                plan_tier=plan_tier,
                session_id=session.id,
            )

            logger.info(f"Created checkout session {session.id} for store {store_id}")

            return {
                "session_id": session.id,
                "url": session.url,
                "customer_id": customer_id,
            }
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error creating checkout session: {e}")
            raise
    
    @staticmethod
    def create_portal_session(
        db: Session,
        store_id: str,
        return_url: str
    ) -> str:
        """Create Stripe Customer Portal session.
        
        Args:
            db: Database session
            store_id: Store UUID
            return_url: URL to redirect after portal
            
        Returns:
            Portal URL
        """
        try:
            _ensure_api_key()
            store = db.query(Store).filter(Store.id == store_id).first()
            if not store or not store.stripe_customer_id:
                raise StripeCustomerMissingError(f"Store {store_id} has no Stripe customer")

            session = stripe.billing_portal.Session.create(
                customer=store.stripe_customer_id,
                return_url=return_url
            )

            log_billing_event(
                "portal_session_created",
                store_id=store_id,
                customer_id=store.stripe_customer_id,
                portal_session=session.id,
            )

            logger.info(f"Created portal session for store {store_id}")
            return {
                "portal_url": session.url,
                "portal_session_id": session.id,
            }
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error creating portal session: {e}")
            raise
    
    @staticmethod
    def sync_subscription_status(db: Session, store_id: str) -> Optional[Subscription]:
        """Sync subscription status from Stripe.
        
        Args:
            db: Database session
            store_id: Store UUID
            
        Returns:
            Updated Subscription or None
        """
        try:
            _ensure_api_key()
            store = db.query(Store).filter(Store.id == store_id).first()
            if not store or not store.stripe_subscription_id:
                return None
            
            # Fetch from Stripe
            stripe_sub = stripe.Subscription.retrieve(store.stripe_subscription_id)
            
            # Update local subscription
            subscription = db.query(Subscription).filter(
                Subscription.store_id == store_id
            ).first()
            
            if subscription:
                subscription.status = stripe_sub.status
                subscription.plan_tier = stripe_sub.metadata.get("plan_tier", "starter")
                subscription.current_period_start = datetime.fromtimestamp(
                    stripe_sub.current_period_start, tz=timezone.utc
                )
                subscription.current_period_end = datetime.fromtimestamp(
                    stripe_sub.current_period_end, tz=timezone.utc
                )
                subscription.cancel_at_period_end = stripe_sub.cancel_at_period_end
                subscription.updated_at = datetime.now(timezone.utc)
                db.commit()
                
                logger.info(f"Synced subscription for store {store_id}")
                return subscription
            
            return None
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error syncing subscription: {e}")
            raise
