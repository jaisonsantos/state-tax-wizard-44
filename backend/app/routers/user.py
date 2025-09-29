from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..core.deps import get_current_user_email
from ..db.database import get_db
from ..models.models import User
from ..schema.auth import MeResponse, StoreSummary, UserSummary

router = APIRouter(tags=["user"])


@router.get("/me", response_model=MeResponse)
async def get_me(
    current_user_email: str = Depends(get_current_user_email),
    db: Session = Depends(get_db),
):
    """Get current user info and associated stores."""

    user = db.query(User).filter(User.email == current_user_email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    store_infos = [
        StoreSummary(
            id=str(store.id),
            name=store.name,
        )
        for store in user.stores
    ]

    user_summary = UserSummary(
        id=str(user.id),
        email=user.email,
        created_at=user.created_at or datetime.utcnow(),
    )

    return MeResponse(user=user_summary, stores=store_infos)
