from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


IntegrationProvider = Literal["shopify", "woocommerce"]


class IntegrationProviderStatus(BaseModel):
    provider: IntegrationProvider
    enabled: bool
    connected: bool
    status: Literal["connected", "disconnected", "disabled"]
    docs_url: str
    install_url: Optional[str] = None
    installed_at: Optional[datetime] = None
    last_synced_at: Optional[datetime] = None
    notes: Optional[str] = None


class IntegrationStatusResponse(BaseModel):
    store_id: str
    providers: list[IntegrationProviderStatus]


class IntegrationInstallRequest(BaseModel):
    store_domain: str
    external_shop_id: Optional[str] = Field(default=None, description="Platform specific identifier")
    metadata: Optional[dict[str, str]] = None


class IntegrationInstallResponse(BaseModel):
    provider: IntegrationProvider
    connected: bool
    status: Literal["connected", "disabled"]
    docs_url: str
    notes: Optional[str] = None

