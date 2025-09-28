from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from ..db.database import get_db
from ..schema.auth import LoginRequest, LoginResponse, UserInfo, StoreInfo
from ..core.security import create_access_token, verify_token
from ..models.models import Store
from datetime import timedelta

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    # Mock authentication - accept any valid email format
    if "@" not in request.email or len(request.password) == 0:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
    
    # Create JWT token
    access_token = create_access_token(data={"sub": request.email})
    
    # Get demo store data
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
    
    return LoginResponse(
        token=access_token,
        user=UserInfo(
            id="demo-user-123",
            email=request.email,
            stores=store_infos
        )
    )