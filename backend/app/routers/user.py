from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..core.deps import get_current_user_email
from ..db.database import get_db
from ..models.models import AuditLog, SessionToken, User
from ..schema.auth import MeResponse, SessionMetadata, StoreSummary, UserSummary

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

    created_at = user.created_at
    if created_at is None:
        created_at = datetime.now(timezone.utc)
    elif created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)

    user_summary = UserSummary(
        id=str(user.id),
        email=user.email,
        created_at=created_at,
    )

    session: SessionMetadata | None = None
    active_session = (
        db.query(SessionToken)
        .filter(SessionToken.user_id == user.id, SessionToken.revoked_at.is_(None))
        .order_by(SessionToken.issued_at.desc())
        .first()
    )

    if active_session:
        last_activity = (
            db.query(AuditLog)
            .filter(AuditLog.actor == f"user:{user.email}")
            .order_by(AuditLog.ts.desc())
            .first()
        )

        session = SessionMetadata(
            id=str(active_session.id),
            issued_at=active_session.issued_at,
            expires_at=active_session.expires_at,
            last_activity_at=last_activity.ts if last_activity else None,
            store_scope=[store.name for store in user.stores],
            ip_address=active_session.ip_address,
            user_agent=active_session.user_agent,
        )

    return MeResponse(user=user_summary, stores=store_infos, session=session)
