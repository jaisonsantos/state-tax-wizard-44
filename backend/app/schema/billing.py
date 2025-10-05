from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class BillingLimits(BaseModel):
    transactions_per_month: Optional[int] = Field(None, ge=0)
    deliveries_included: Optional[int] = Field(None, ge=0)
    warn_threshold_pct: int = Field(80, ge=0, le=100)
    unlimited: bool = False
    commit_deliveries: Optional[int] = Field(None, ge=0)
    overage_fee: Optional[float] = Field(None, ge=0)
    advanced_reports: bool = False
    analytics_dashboard: bool = False
    integrations: bool = False


class Entitlements(BaseModel):
    plan: str
    display_name: Optional[str] = None
    provider: str
    status: str
    monthly_price: Optional[float] = None
    annual_price: Optional[float] = None
    deliveries_included: Optional[int] = None
    warn_threshold_pct: int = Field(80, ge=0, le=100)
    unlimited: bool = False
    commit_deliveries: Optional[int] = Field(None, ge=0)
    overage_fee: Optional[float] = Field(None, ge=0)
    trial_ends_at: Optional[datetime] = None
    cancel_at_period_end: bool = False
    current_period_start: Optional[datetime] = None
    current_period_end: Optional[datetime] = None
    features: List[str] = []
    limits: BillingLimits
    stripe_prices_configured: Dict[str, bool] = Field(default_factory=dict)


class EnterpriseOverage(BaseModel):
    commit_deliveries: int = Field(..., ge=1)
    overage_units: int = Field(..., ge=1)
    overage_fee: Optional[float] = Field(None, ge=0)
    estimated_overage_cost: float = Field(..., ge=0)


class UsageResponse(BaseModel):
    plan: str
    status: str
    transactions_used: int = Field(..., ge=0)
    transactions_limit: Optional[int] = Field(None, ge=0)
    unlimited: bool
    percentage_used: float = Field(..., ge=0)
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    warn_threshold_pct: int = Field(80, ge=0, le=100)
    warnings: List[str] = []
    enterprise_overage: Optional[EnterpriseOverage] = None


class CheckoutSessionRequest(BaseModel):
    plan_tier: str = Field(
        ...,
        description="Desired subscription tier",
        pattern="^(free|starter|pro|plus|enterprise_e10k|enterprise_e25k|enterprise_e50k)$",
    )
    success_url: str
    cancel_url: str


class CheckoutSessionResponse(BaseModel):
    session_id: str
    url: str


class PortalSessionResponse(BaseModel):
    portal_url: str
    portal_session_id: str
