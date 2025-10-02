from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class PlanSummary(BaseModel):
    name: str
    price: str
    currency: str
    interval: str
    highlight: bool = False
    description: Optional[str] = None


class UsageBreakdown(BaseModel):
    transactions_used: int = Field(0, ge=0)
    transactions_limit: int = Field(..., ge=0)
    api_calls_used: int = Field(0, ge=0)
    api_calls_limit: int = Field(..., ge=0)
    last_reset_at: Optional[datetime] = None
    next_reset_at: Optional[datetime] = None


class Entitlements(BaseModel):
    plan: str
    provider: str  # "shopify" or "stripe"
    status: str  # "trialing", "active", "past_due", "cancelled"
    trial_ends_at: Optional[datetime] = None
    cancel_at_period_end: bool = False
    current_period_end: Optional[datetime] = None


class CheckoutSessionRequest(BaseModel):
    plan: str
    success_url: str
    cancel_url: str


class CheckoutSessionResponse(BaseModel):
    url: str
    session_id: str


class PortalSessionResponse(BaseModel):
    url: str


class UsageResponse(BaseModel):
    plan: str
    usage: UsageBreakdown
    entitlements: Entitlements
    available_plans: List[PlanSummary] = []
