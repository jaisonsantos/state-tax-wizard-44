from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from ..db.database import get_db
from ..schema.auth import UserInfo, StoreInfo
from ..core.security import verify_token
from ..models.models import Store
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

@router.get("/me", response_model=UserInfo)
async def get_me(current_user: str = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get current user info and associated stores"""
    
    # Get demo stores
    stores = db.query(Store).limit(5).all()
    store_infos = [
        StoreInfo(
            id=str(store.id),
            platform=store.platform,
            domain=store.domain,
            country=store.country,
            state=store.state,
            created_at=store.created_at
        ) for store in stores
    ]
    
    return UserInfo(
        id="demo-user-123",
        email=current_user,
        stores=store_infos
    )