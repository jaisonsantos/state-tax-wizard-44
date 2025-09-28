from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from ..db.database import get_db
from ..schema.auth import MeResponse, StoreSummary, UserSummary
from ..core.security import verify_token
from ..models.models import User
from typing import Optional

router = APIRouter(tags=["user"])

async def get_current_user(authorization: Optional[str] = Header(None)):
    """Get current user from JWT token"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authorization header required")

    token = authorization.split(" ")[1]
    email = verify_token(token)

    if not email:
        raise HTTPException(status_code=401, detail="Invalid token")

    return email

@router.get("/me", response_model=MeResponse)
async def get_me(current_user_email: str = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get current user info and associated stores"""

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