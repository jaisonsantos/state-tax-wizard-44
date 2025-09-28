from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class Entitlements(BaseModel):
    plan: str
    trial_ends_at: Optional[datetime] = None
    provider: str  # "shopify" or "stripe"
    status: str  # "trialing", "active", "past_due", "cancelled"