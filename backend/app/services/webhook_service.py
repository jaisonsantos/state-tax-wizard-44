"""Webhook service for processing Stripe events."""
import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from ..models.models import AuditLog, Store, Subscription
from ..observability import log_billing_event

logger = logging.getLogger(__name__)


class WebhookService:
    """Service for processing Stripe webhook events."""
    
    @staticmethod
    def process_subscription_created(db: Session, event: dict):
        """Process subscription.created event.
        
        Args:
            db: Database session
            event: Stripe event object
        """
        try:
            subscription_obj = event["data"]["object"]
            customer_id = subscription_obj["customer"]
            subscription_id = subscription_obj["id"]
            
            # Find store by customer ID
            store = db.query(Store).filter(
                Store.stripe_customer_id == customer_id
            ).first()
            
            if not store:
                logger.error(f"Store not found for customer {customer_id}")
                return
            
            # Extract plan tier from metadata
            plan_tier = subscription_obj.get("metadata", {}).get("plan_tier", "starter")
            
            # Create or update subscription
            subscription = db.query(Subscription).filter(
                Subscription.store_id == store.id
            ).first()
            
            if not subscription:
                subscription = Subscription(
                    store_id=store.id,
                    provider="stripe",
                    plan=plan_tier,
                    plan_tier=plan_tier
                )
                db.add(subscription)
            
            subscription.stripe_subscription_id = subscription_id
            subscription.stripe_customer_id = customer_id
            subscription.status = subscription_obj["status"]
            subscription.current_period_start = datetime.fromtimestamp(
                subscription_obj["current_period_start"], tz=timezone.utc
            )
            subscription.current_period_end = datetime.fromtimestamp(
                subscription_obj["current_period_end"], tz=timezone.utc
            )
            subscription.cancel_at_period_end = subscription_obj.get("cancel_at_period_end", False)
            subscription.trial_end = (
                datetime.fromtimestamp(subscription_obj["trial_end"], tz=timezone.utc)
                if subscription_obj.get("trial_end") else None
            )
            
            # Update store subscription ID
            store.stripe_subscription_id = subscription_id
            
            # Create audit log
            audit_log = AuditLog(
                store_id=store.id,
                action="stripe_webhook",
                payload={
                    "event_type": "subscription.created",
                    "subscription_id": subscription_id,
                    "plan_tier": plan_tier,
                    "status": subscription_obj["status"]
                }
            )
            db.add(audit_log)
            
            db.commit()
            
            log_billing_event(
                "subscription_created",
                store_id=str(store.id),
                plan_tier=plan_tier,
                subscription_id=subscription_id
            )
            
            logger.info(f"Processed subscription.created for store {store.id}")
            
        except Exception as e:
            logger.error(f"Error processing subscription.created: {e}")
            db.rollback()
            raise
    
    @staticmethod
    def process_subscription_updated(db: Session, event: dict):
        """Process subscription.updated event.
        
        Args:
            db: Database session
            event: Stripe event object
        """
        try:
            subscription_obj = event["data"]["object"]
            subscription_id = subscription_obj["id"]
            
            # Find subscription
            subscription = db.query(Subscription).filter(
                Subscription.stripe_subscription_id == subscription_id
            ).first()
            
            if not subscription:
                logger.error(f"Subscription not found: {subscription_id}")
                return
            
            # Update subscription
            old_status = subscription.status
            subscription.status = subscription_obj["status"]
            subscription.current_period_start = datetime.fromtimestamp(
                subscription_obj["current_period_start"], tz=timezone.utc
            )
            subscription.current_period_end = datetime.fromtimestamp(
                subscription_obj["current_period_end"], tz=timezone.utc
            )
            subscription.cancel_at_period_end = subscription_obj.get("cancel_at_period_end", False)
            subscription.updated_at = datetime.now(timezone.utc)
            
            # Create audit log
            audit_log = AuditLog(
                store_id=subscription.store_id,
                action="stripe_webhook",
                payload={
                    "event_type": "subscription.updated",
                    "subscription_id": subscription_id,
                    "old_status": old_status,
                    "new_status": subscription_obj["status"],
                    "cancel_at_period_end": subscription_obj.get("cancel_at_period_end", False)
                }
            )
            db.add(audit_log)
            
            db.commit()
            
            log_billing_event(
                "subscription_updated",
                store_id=str(subscription.store_id),
                old_status=old_status,
                new_status=subscription_obj["status"]
            )
            
            logger.info(f"Processed subscription.updated for subscription {subscription_id}")
            
        except Exception as e:
            logger.error(f"Error processing subscription.updated: {e}")
            db.rollback()
            raise
    
    @staticmethod
    def process_subscription_deleted(db: Session, event: dict):
        """Process subscription.deleted event.
        
        Args:
            db: Database session
            event: Stripe event object
        """
        try:
            subscription_obj = event["data"]["object"]
            subscription_id = subscription_obj["id"]
            
            # Find subscription
            subscription = db.query(Subscription).filter(
                Subscription.stripe_subscription_id == subscription_id
            ).first()
            
            if not subscription:
                logger.error(f"Subscription not found: {subscription_id}")
                return
            
            # Update status to canceled
            subscription.status = "canceled"
            subscription.updated_at = datetime.now(timezone.utc)
            
            # Create audit log
            audit_log = AuditLog(
                store_id=subscription.store_id,
                action="stripe_webhook",
                payload={
                    "event_type": "subscription.deleted",
                    "subscription_id": subscription_id
                }
            )
            db.add(audit_log)
            
            db.commit()
            
            log_billing_event(
                "subscription_deleted",
                store_id=str(subscription.store_id),
                subscription_id=subscription_id
            )
            
            logger.info(f"Processed subscription.deleted for subscription {subscription_id}")
            
        except Exception as e:
            logger.error(f"Error processing subscription.deleted: {e}")
            db.rollback()
            raise
    
    @staticmethod
    def process_invoice_paid(db: Session, event: dict):
        """Process invoice.paid event.
        
        Args:
            db: Database session
            event: Stripe event object
        """
        try:
            invoice_obj = event["data"]["object"]
            subscription_id = invoice_obj.get("subscription")
            
            if not subscription_id:
                return
            
            # Find subscription
            subscription = db.query(Subscription).filter(
                Subscription.stripe_subscription_id == subscription_id
            ).first()
            
            if not subscription:
                logger.error(f"Subscription not found: {subscription_id}")
                return
            
            # Update billing period
            if invoice_obj.get("period_start") and invoice_obj.get("period_end"):
                subscription.current_period_start = datetime.fromtimestamp(
                    invoice_obj["period_start"], tz=timezone.utc
                )
                subscription.current_period_end = datetime.fromtimestamp(
                    invoice_obj["period_end"], tz=timezone.utc
                )
                subscription.updated_at = datetime.now(timezone.utc)
            
            # Create audit log
            audit_log = AuditLog(
                store_id=subscription.store_id,
                action="stripe_webhook",
                payload={
                    "event_type": "invoice.paid",
                    "invoice_id": invoice_obj["id"],
                    "subscription_id": subscription_id,
                    "amount_paid": invoice_obj.get("amount_paid", 0) / 100
                }
            )
            db.add(audit_log)
            
            db.commit()
            
            log_billing_event(
                "invoice_paid",
                store_id=str(subscription.store_id),
                subscription_id=subscription_id,
                amount=invoice_obj.get("amount_paid", 0) / 100
            )
            
            logger.info(f"Processed invoice.paid for subscription {subscription_id}")
            
        except Exception as e:
            logger.error(f"Error processing invoice.paid: {e}")
            db.rollback()
            raise
    
    @staticmethod
    def process_invoice_payment_failed(db: Session, event: dict):
        """Process invoice.payment_failed event.
        
        Args:
            db: Database session
            event: Stripe event object
        """
        try:
            invoice_obj = event["data"]["object"]
            subscription_id = invoice_obj.get("subscription")
            
            if not subscription_id:
                return
            
            # Find subscription
            subscription = db.query(Subscription).filter(
                Subscription.stripe_subscription_id == subscription_id
            ).first()
            
            if not subscription:
                logger.error(f"Subscription not found: {subscription_id}")
                return
            
            # Create audit log
            audit_log = AuditLog(
                store_id=subscription.store_id,
                action="stripe_webhook",
                payload={
                    "event_type": "invoice.payment_failed",
                    "invoice_id": invoice_obj["id"],
                    "subscription_id": subscription_id,
                    "attempt_count": invoice_obj.get("attempt_count", 0)
                }
            )
            db.add(audit_log)
            
            db.commit()
            
            log_billing_event(
                "invoice_payment_failed",
                store_id=str(subscription.store_id),
                subscription_id=subscription_id
            )
            
            logger.warning(f"Payment failed for subscription {subscription_id}")
            
        except Exception as e:
            logger.error(f"Error processing invoice.payment_failed: {e}")
            db.rollback()
            raise
