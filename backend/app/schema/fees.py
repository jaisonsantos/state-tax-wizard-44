from typing import List, Literal, Optional

from pydantic import BaseModel


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
    source_of_remittance: Optional[Literal["merchant", "marketplace"]] = None


class FeeLine(BaseModel):
    jurisdiction: str  # "MN" or "CO"
    amount_cents: int
    display_name: str
    rule_version: str
    reason_codes: List[str]
    absorbed: bool = False


class FeeDecision(BaseModel):
    jurisdiction: str
    outcome: Literal["applied", "skipped"]
    reason_codes: List[str]
    amount_cents: int


class FeeQuoteResponse(BaseModel):
    lines: List[FeeLine]
    decisions: List[FeeDecision]
    decided: bool
    absorbed: bool


class FeeApplyRequest(BaseModel):
    store_id: str
    order_id: str
    destination: FeeDestination
    delivery_method: str
    items: List[FeeItem]
    shipping_amount_cents: int
    source_of_remittance: Optional[Literal["merchant", "marketplace"]] = None


class FeeApplyResponse(BaseModel):
    success: bool
    lines: List[FeeLine]
    decisions: List[FeeDecision]
    absorbed: bool


class FeeReversalRequest(BaseModel):
    store_id: str
    order_id: str
    reason: Literal["DELIVERY_CANCELLED", "RETURN_POST_DELIVERY"]


class FeeReversalResponse(BaseModel):
    success: bool
    refunded_amount_cents: int
    reversed_jurisdictions: List[str]
    reason: str
