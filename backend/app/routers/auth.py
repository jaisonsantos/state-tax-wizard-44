from datetime import datetime
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..core.security import create_access_token
from ..db.database import get_db
from ..models.models import Store, StoreSetting, User, UserStore
from ..schema.auth import LoginRequest, LoginResponse, StoreSummary, UserSummary

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    # Mock authentication - accept any valid email format
    if "@" not in request.email or len(request.password) == 0:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    # Ensure seed store exists
    seed_store = db.query(Store).filter(Store.name == "store_demo_1").first()
    if not seed_store:
        seed_store = Store(
            id=uuid.uuid4(),
            name="store_demo_1",
            platform="shopify",
            domain="store_demo_1.myshopify.com",
            country="US",
            state="MN",
        )
        db.add(seed_store)
        db.flush()

        # Ensure the store has default settings
        setting = StoreSetting(
            store_id=seed_store.id,
            enable_mn=True,
            enable_co=True,
            absorb_fee=False,
            label_override="Delivery Fee",
            plan="starter",
        )
        db.add(setting)

    user = db.query(User).filter(User.email == request.email).first()

    created = False
    if not user:
        user = User(email=request.email)
        db.add(user)
        db.flush()
        created = True

    if seed_store not in user.stores:
        link = UserStore(user_id=user.id, store_id=seed_store.id)
        db.add(link)
        created = True

    if created:
        db.commit()
    else:
        db.flush()

    db.refresh(user)
    db.refresh(seed_store)

    store_infos = [
        StoreSummary(
            id=str(store.id),
            name=store.name,
        )
        for store in user.stores
    ]

    store_ids = [str(store.id) for store in user.stores]

    user_summary = UserSummary(
        id=str(user.id),
        email=user.email,
        created_at=user.created_at or datetime.utcnow(),
    )

    access_token = create_access_token(
        email=user.email,
        stores=store_ids,
    )

    return LoginResponse(
        token=access_token,
        user=user_summary,
        stores=store_infos,
    )
