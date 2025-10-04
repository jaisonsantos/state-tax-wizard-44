from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..core.deps import AuthContext, assert_store_access, get_auth_context
from ..db.database import get_db
from ..models.models import StoreSetting, WebhookEvent
from ..schema.webhooks import WebhookEventListResponse, WebhookReplayResponse
from ..services.taxo_webhook_service import QueuedEvent, TaxoWebhookService


router = APIRouter(prefix="/v1/webhooks", tags=["webhooks"])


@router.get("/events", response_model=WebhookEventListResponse)
async def list_webhook_events(
    store_id: str = Query(...),
    status: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_auth_context),
):
    """Return recent webhook events for the requested store."""

    assert_store_access(db, auth, store_id)

    query = db.query(WebhookEvent).filter(WebhookEvent.store_id == store_id)
    if status:
        query = query.filter(WebhookEvent.status == status)

    events = (
        query.order_by(WebhookEvent.created_at.desc())
        .limit(limit)
        .all()
    )

    return WebhookEventListResponse(events=events)


@router.post("/events/{event_id}/replay", response_model=WebhookReplayResponse)
async def replay_webhook_event(
    event_id: str,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_auth_context),
):
    """Manually replay a webhook event for diagnostics or recovery."""

    event = (
        db.query(WebhookEvent)
        .filter(WebhookEvent.event_id == event_id)
        .first()
    )
    if not event:
        raise HTTPException(status_code=404, detail="Webhook event not found")

    store_id = str(event.store_id)
    assert_store_access(db, auth, store_id)

    settings = (
        db.query(StoreSetting)
        .filter(StoreSetting.store_id == store_id)
        .first()
    )

    event.dead_letter = False
    event.status = "pending"
    event.attempts = 0
    event.last_error = None
    event.next_retry_at = None
    event.delivered_at = None
    db.add(event)
    db.commit()
    db.refresh(event)

    queued = QueuedEvent(event_id=event.event_id, event_type=event.event_type)
    TaxoWebhookService.dispatch_events(
        db,
        store_id,
        [queued],
        settings_model=settings,
    )
    db.commit()
    db.refresh(event)

    return WebhookReplayResponse(
        event_id=event.event_id,
        status=event.status,
        attempts=event.attempts,
        next_retry_at=event.next_retry_at,
        dead_letter=event.dead_letter,
    )
