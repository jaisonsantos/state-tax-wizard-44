from pydantic import BaseModel
from typing import List, Optional
import uuid

class FeeItem(BaseModel):
    sku: str
    qty: int
    unit_price_cents: int
    taxability: str  # "taxable", "exempt", "clothing"

class FeeDestination(BaseModel):
    state: str
    zip: Optional[str] = None

class FeeQuoteRequest(BaseModel):
    store_id: str
    destination: FeeDestination
    delivery_method: str  # "ship", "pickup", "curbside"
    items: List[FeeItem]
    shipping_amount_cents: int

class FeeLine(BaseModel):
    jurisdiction: str  # "MN" or "CO"
    amount_cents: int
    display_name: str
    rule_version: str
    reason_codes: List[str]

class FeeQuoteResponse(BaseModel):
    lines: List[FeeLine]
    decided: bool

class FeeApplyRequest(BaseModel):
    store_id: str
    order_id: str
    destination: FeeDestination
    delivery_method: str
    items: List[FeeItem]
    shipping_amount_cents: int

class FeeApplyResponse(BaseModel):
    success: bool
    lines: List[FeeLine]