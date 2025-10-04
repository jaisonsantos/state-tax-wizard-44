from datetime import datetime, timezone
import secrets
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..core.deps import AuthContext, assert_store_access, get_auth_context
from ..db.database import get_db
from ..models.models import AuditLog, Store, StoreSetting
from ..schema.store_settings import (
    RotateHmacSecretResponse,
    StoreSettingsResponse,
    UpdateStoreSettingsRequest,
)
from ..services.entitlement_service import EntitlementService
from ..services.taxo_webhook_service import TaxoWebhookService

TAXO_EVENT_CATALOG = {"fee.applied", "fee.skipped", "report.ready", "hmac.rotated"}


router = APIRouter(prefix="/v1/stores", tags=["store-settings"])


def _get_or_create_settings(db: Session, store_id: str) -> StoreSetting:
    settings = (
        db.query(StoreSetting)
        .filter(StoreSetting.store_id == store_id)
        .first()
    )
    if settings:
        return settings

    settings = StoreSetting(store_id=store_id)
    db.add(settings)
    db.commit()
    db.refresh(settings)
    return settings


def _resolve_plan_slug(
    db: Session, store_id: str, fallback: Optional[str] = None
) -> Optional[str]:
    """Determine the active plan for a store based on subscription data."""

    subscription = EntitlementService.get_subscription(db, store_id)
    plan_tier = getattr(subscription, "plan_tier", None) or getattr(subscription, "plan", None)

    if isinstance(plan_tier, str) and plan_tier:
        return plan_tier.lower()

    if isinstance(fallback, str) and fallback:
        return fallback.lower()

    return fallback


@router.get("/{store_id}/settings", response_model=StoreSettingsResponse)
async def get_store_settings(
    store_id: str,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_auth_context),
):
    """Return the persisted delivery fee settings for the requested store."""

    assert_store_access(db, auth, store_id)

    store = db.query(Store).filter(Store.id == store_id).first()
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")

    settings = _get_or_create_settings(db, store_id)
    plan = _resolve_plan_slug(db, store_id, settings.plan)

    return StoreSettingsResponse(
        store_id=str(store_id),
        enable_mn=settings.enable_mn,
        enable_co=settings.enable_co,
        absorb_fee=settings.absorb_fee,
        label_override=settings.label_override,
        plan=plan,
        hmac_last_rotated_at=settings.hmac_secret_rotated_at,
        webhook_active=bool(settings.webhook_active and settings.webhook_endpoint),
        webhook_endpoint=settings.webhook_endpoint,
        webhook_events=list(settings.webhook_events or []),
    )


@router.post("/{store_id}/hmac/rotate", response_model=RotateHmacSecretResponse)
async def rotate_hmac_secret(
    store_id: str,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_auth_context),
):
    """Rotate the HMAC secret for a store and return the new value."""

    assert_store_access(db, auth, store_id)

    store = db.query(Store).filter(Store.id == store_id).first()
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")

    settings = _get_or_create_settings(db, store_id)

    new_secret = secrets.token_urlsafe(48)
    now = datetime.now(timezone.utc)
    previous_rotated_at = settings.hmac_secret_rotated_at

    settings.hmac_secret = new_secret
    settings.hmac_secret_rotated_at = now

    audit_log = AuditLog(
        actor=f"user:{auth.email}",
        action="store_secret.rotated",
        payload={
            "store_id": store_id,
            "rotated_at": now.isoformat(),
            "previous_rotated_at": previous_rotated_at.isoformat()
            if previous_rotated_at
            else None,
        },
    )

    db.add(settings)
    db.add(audit_log)
    queued = TaxoWebhookService.queue_hmac_rotated(
        db,
        store_id=store_id,
        rotated_at=now,
        previous_rotated_at=previous_rotated_at,
        actor=auth.email,
    )

    db.commit()
    db.refresh(settings)

    if queued:
        TaxoWebhookService.dispatch_events(
            db,
            store_id,
            [queued],
            settings_model=settings,
        )
        db.commit()

    return RotateHmacSecretResponse(
        store_id=str(store_id),
        hmac_secret=new_secret,
        rotated_at=now,
        previous_rotated_at=previous_rotated_at,
    )


@router.put("/{store_id}/settings", response_model=StoreSettingsResponse)
async def update_store_settings(
    store_id: str,
    payload: UpdateStoreSettingsRequest,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_auth_context),
):
    """Update the delivery fee configuration for a store and return the new values."""

    assert_store_access(db, auth, store_id)

    store = db.query(Store).filter(Store.id == store_id).first()
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")

    settings = _get_or_create_settings(db, store_id)

    settings.enable_mn = payload.enable_mn
    settings.enable_co = payload.enable_co
    settings.absorb_fee = payload.absorb_fee
    settings.label_override = payload.label_override.strip()
    plan = _resolve_plan_slug(db, store_id, settings.plan)
    if plan and settings.plan != plan:
        settings.plan = plan

    if payload.webhook_active is not None:
        settings.webhook_active = payload.webhook_active
    if payload.webhook_endpoint is not None:
        endpoint = payload.webhook_endpoint.strip()
        settings.webhook_endpoint = endpoint or None
    if payload.webhook_events is not None:
        cleaned_events: list[str] = []
        for candidate in payload.webhook_events:
            if not candidate:
                continue
            event = candidate.strip()
            if event in TAXO_EVENT_CATALOG and event not in cleaned_events:
                cleaned_events.append(event)
        settings.webhook_events = cleaned_events

    db.add(settings)

    audit_log = AuditLog(
        actor=f"user:{auth.email}",
        action="store_settings.update",
        payload={
            "store_id": store_id,
            "changes": payload.model_dump(),
        },
    )
    db.add(audit_log)

    db.commit()
    db.refresh(settings)

    return StoreSettingsResponse(
        store_id=str(store_id),
        enable_mn=settings.enable_mn,
        enable_co=settings.enable_co,
        absorb_fee=settings.absorb_fee,
        label_override=settings.label_override,
        plan=_resolve_plan_slug(db, store_id, settings.plan),
        hmac_last_rotated_at=settings.hmac_secret_rotated_at,
        webhook_active=bool(settings.webhook_active and settings.webhook_endpoint),
        webhook_endpoint=settings.webhook_endpoint,
        webhook_events=list(settings.webhook_events or []),
    )
