from __future__ import annotations

import logging
from typing import Dict

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..core.config import settings
from ..core.deps import AuthContext, assert_store_access, get_auth_context
from ..db.database import get_db
from ..models.models import AuditLog, Store
from ..observability import (
    record_integration_error,
    record_integration_request,
)
from ..schema.integrations import (
    IntegrationInstallRequest,
    IntegrationInstallResponse,
    IntegrationProvider,
    IntegrationProviderStatus,
    IntegrationStatusResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/integrations", tags=["integrations"])

_PROVIDER_SLUG = {
    "shopify": "shopify",
    "woocommerce": "woo",
}

_DOCS_URL = {
    "shopify": "/api/files/docs/integrations/shopify.md",
    "woocommerce": "/api/files/docs/integrations/woocommerce.md",
}

_INSTALL_URL = {
    "shopify": "https://apps.shopify.com/state-tax-wizard",
    "woocommerce": "https://wordpress.org/plugins/state-tax-wizard/",
}


def _provider_enabled(provider: IntegrationProvider) -> bool:
    if provider == "shopify":
        return settings.integrations_shopify_enabled
    if provider == "woocommerce":
        return settings.integrations_woo_enabled
    return False


def _build_provider_status(store: Store, provider: IntegrationProvider) -> IntegrationProviderStatus:
    enabled = _provider_enabled(provider)
    platform_slug = _PROVIDER_SLUG[provider]
    connected = enabled and (store.platform or "").lower() == platform_slug
    status = "disabled" if not enabled else ("connected" if connected else "disconnected")

    notes = None
    if not enabled:
        notes = "Feature flag disabled for this provider"
    elif not connected:
        notes = "Provider enabled but store not connected"

    record_integration_request(provider, "status")

    return IntegrationProviderStatus(
        provider=provider,
        enabled=enabled,
        connected=connected,
        status=status,
        docs_url=_DOCS_URL[provider],
        install_url=_INSTALL_URL[provider],
        installed_at=store.updated_at if hasattr(store, "updated_at") else None,
        notes=notes,
    )


@router.get("/status", response_model=IntegrationStatusResponse)
async def get_integration_status(
    store_id: str = Query(...),
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_auth_context),
) -> IntegrationStatusResponse:
    """Return integration readiness for the given store with feature flag awareness."""

    assert_store_access(db, auth, store_id)

    store = db.query(Store).filter(Store.id == store_id).first()
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")

    providers = [
        _build_provider_status(store, provider)
        for provider in ("shopify", "woocommerce")
    ]

    return IntegrationStatusResponse(store_id=str(store.id), providers=providers)


@router.post("/providers/{provider}/install", response_model=IntegrationInstallResponse)
async def install_integration(
    provider: IntegrationProvider,
    payload: IntegrationInstallRequest,
    store_id: str = Query(...),
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_auth_context),
) -> IntegrationInstallResponse:
    """Mark a store as connected to a provider once the operator completes setup."""

    assert_store_access(db, auth, store_id)
    store = db.query(Store).filter(Store.id == store_id).first()
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")

    record_integration_request(provider, "install")

    if not _provider_enabled(provider):
        record_integration_error(provider, "disabled")
        raise HTTPException(
            status_code=503,
            detail={"code": "integration_disabled", "message": f"{provider} integration is disabled"},
        )

    platform_slug = _PROVIDER_SLUG[provider]
    store.platform = platform_slug
    if payload.store_domain:
        store.domain = payload.store_domain.lower()

    # Record an audit entry to trace configuration changes without storing secrets.
    audit_payload: Dict[str, str] = {
        "store_id": str(store.id),
        "provider": provider,
        "store_domain": store.domain,
    }
    if payload.external_shop_id:
        audit_payload["external_shop_id"] = payload.external_shop_id

    db.add(
        AuditLog(
            actor="integrations_api",
            action="integration_install",
            payload=audit_payload,
        )
    )

    try:
        db.commit()
    except Exception as exc:  # pragma: no cover - defensive
        db.rollback()
        logger.exception("Failed to persist integration install for %s", provider)
        record_integration_error(provider, "persist_failure")
        raise HTTPException(status_code=500, detail="Failed to persist integration state") from exc

    notes = "Store marked as connected to provider"

    return IntegrationInstallResponse(
        provider=provider,
        connected=True,
        status="connected",
        docs_url=_DOCS_URL[provider],
        notes=notes,
    )

