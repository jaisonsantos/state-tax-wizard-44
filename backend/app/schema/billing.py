from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class BillingLimits(BaseModel):
    transactions_per_month: Optional[int] = Field(None, ge=0)
    advanced_reports: bool = False
    analytics_dashboard: bool = False
    integrations: bool = False


class Entitlements(BaseModel):
    plan: str
    provider: str
    status: str
    trial_ends_at: Optional[datetime] = None
    cancel_at_period_end: bool = False
    current_period_start: Optional[datetime] = None
    current_period_end: Optional[datetime] = None
    features: List[str] = []
    limits: BillingLimits


class UsageResponse(BaseModel):
    plan: str
    status: str
    transactions_used: int = Field(..., ge=0)
    transactions_limit: Optional[int] = Field(None, ge=0)
    unlimited: bool
    percentage_used: float = Field(..., ge=0)
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None


class CheckoutSessionRequest(BaseModel):
    plan_tier: str = Field(..., description="Desired subscription tier", pattern="^(starter|pro|plus)$")
    success_url: str
    cancel_url: str


class CheckoutSessionResponse(BaseModel):
    session_id: str
    url: str


class PortalSessionResponse(BaseModel):
    portal_url: str
    portal_session_id: str
