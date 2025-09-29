from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..core.deps import AuthContext, assert_store_access, get_auth_context
from ..db.database import get_db
from ..models.models import Subscription
from ..schema.billing import Entitlements

router = APIRouter(prefix="/v1/billing", tags=["billing"])


@router.get("/entitlements", response_model=Entitlements)
async def get_entitlements(
    store_id: str = Query(...),
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_auth_context),
):
    """Get billing entitlements for a store"""

    assert_store_access(db, auth, store_id)

    # Get subscription for store
    subscription = db.query(Subscription).filter(
        Subscription.store_id == store_id
    ).first()

    if subscription:
        return Entitlements(
            plan=subscription.plan,
            trial_ends_at=subscription.trial_end,
            provider=subscription.provider,
            status=subscription.status,
        )

    # Default trial subscription
    return Entitlements(
        plan="starter",
        trial_ends_at=datetime(2024, 2, 1),  # 14 days from "signup"
        provider="stripe",
        status="trialing",
    )
