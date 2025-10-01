from datetime import datetime, timezone
import secrets

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

    return StoreSettingsResponse(
        store_id=str(store_id),
        enable_mn=settings.enable_mn,
        enable_co=settings.enable_co,
        absorb_fee=settings.absorb_fee,
        label_override=settings.label_override,
        plan=settings.plan,
        hmac_last_rotated_at=settings.hmac_secret_rotated_at,
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
    db.commit()
    db.refresh(settings)

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
        plan=settings.plan,
        hmac_last_rotated_at=settings.hmac_secret_rotated_at,
    )
