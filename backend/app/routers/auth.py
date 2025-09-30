from datetime import datetime, timedelta, timezone
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from ..core.deps import AuthContext, get_auth_context
from ..core.security import create_access_token
from ..db.database import get_db
from ..models.models import SessionToken, Store, StoreSetting, User, UserStore
from ..observability import auth_events_total, log_auth_event
from ..schema.auth import LoginRequest, LoginResponse, StoreSummary, UserSummary
from ..core.config import settings

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
async def login(
    request: LoginRequest,
    raw_request: Request,
    db: Session = Depends(get_db),
):
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

    session_jti = str(uuid.uuid4())
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)

    access_token = create_access_token(
        email=user.email,
        stores=store_ids,
        jti=session_jti,
        expires_delta=timedelta(minutes=settings.jwt_expire_minutes),
    )

    session_token = SessionToken(
        user_id=user.id,
        jti=session_jti,
        expires_at=expires_at,
        user_agent=raw_request.headers.get("User-Agent"),
        ip_address=raw_request.client.host if raw_request.client else None,
    )
    db.add(session_token)
    db.commit()

    auth_events_total.labels(event="login").inc()
    log_auth_event(
        {
            "event": "login",
            "subject": user.email,
            "user_id": str(user.id),
            "session_id": str(session_token.id),
            "jti": session_jti,
            "stores": store_ids,
        }
    )

    return LoginResponse(
        token=access_token,
        user=user_summary,
        stores=store_infos,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
) -> Response:
    session = (
        db.query(SessionToken)
        .filter(SessionToken.id == uuid.UUID(auth.session_id))
        .first()
    )

    if not session or session.revoked_at is not None:
        # Session already revoked or missing; treat as success to avoid leaking state
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    session.revoked_at = datetime.now(timezone.utc)
    session.revoked_reason = "user_logout"
    db.add(session)
    db.commit()

    auth_events_total.labels(event="logout").inc()
    log_auth_event(
        {
            "event": "logout",
            "subject": auth.email,
            "user_id": auth.user_id,
            "session_id": auth.session_id,
        }
    )

    return Response(status_code=status.HTTP_204_NO_CONTENT)
