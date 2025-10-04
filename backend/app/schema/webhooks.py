from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict


class WebhookEventRecord(BaseModel):
    """Representation of a stored webhook event."""

    model_config = ConfigDict(from_attributes=True)

    event_id: str
    event_type: str
    status: str
    attempts: int
    next_retry_at: Optional[datetime] = None
    last_error: Optional[str] = None
    delivered_at: Optional[datetime] = None
    dead_letter: bool
    created_at: datetime
    updated_at: datetime


class WebhookEventListResponse(BaseModel):
    """Envelope for webhook event listings."""

    events: List[WebhookEventRecord]


class WebhookReplayResponse(BaseModel):
    """Response payload for manual webhook replays."""

    event_id: str
    status: str
    attempts: int
    next_retry_at: Optional[datetime] = None
    dead_letter: bool
