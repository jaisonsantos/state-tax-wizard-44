from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class StoreSettingsResponse(BaseModel):
    """Represents the persisted configuration for a store's delivery fee rules."""

    model_config = ConfigDict(from_attributes=True)

    store_id: str = Field(..., description="Store identifier")
    enable_mn: bool = Field(..., description="Whether Minnesota delivery fees are evaluated")
    enable_co: bool = Field(..., description="Whether Colorado delivery fees are evaluated")
    absorb_fee: bool = Field(..., description="If true, the shopper does not see the fee line item")
    label_override: str = Field(..., description="Custom label shown when the fee is visible")
    plan: Optional[str] = Field(None, description="Billing plan associated with the store")
    hmac_last_rotated_at: Optional[datetime] = Field(
        None,
        description="Timestamp of the most recent HMAC secret rotation",
    )


class UpdateStoreSettingsRequest(BaseModel):
    """Payload used to update the delivery fee configuration for a store."""

    enable_mn: bool
    enable_co: bool
    absorb_fee: bool
    label_override: str = Field(min_length=1, max_length=120)
