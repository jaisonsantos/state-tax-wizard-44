from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from ..db.database import get_db
from ..models.models import SessionToken, User
from .security import TokenPayload, verify_token


@dataclass
class AuthContext:
    """Represents the authenticated subject and authorized stores."""

    subject: str
    store_ids: set[str]
    token: str
    user_id: str
    session_id: str

    @property
    def email(self) -> str:
        return self.subject


def get_auth_context(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> AuthContext:
    """Parse the Authorization header and validate the bearer token."""

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header required",
        )

    token = authorization.split(" ", 1)[1].strip()
    payload: Optional[TokenPayload] = verify_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    session = (
        db.query(SessionToken)
        .join(User)
        .filter(SessionToken.jti == payload.jti)
        .first()
    )

    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session not found",
        )

    if session.user.email != payload.sub:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session subject mismatch",
        )

    if session.revoked_at is not None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session revoked",
        )

    now = datetime.now(timezone.utc)
    expires_at = session.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if expires_at <= now:
        session.revoked_at = session.revoked_at or now
        session.revoked_reason = session.revoked_reason or "expired"
        db.add(session)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired",
        )

    return AuthContext(
        subject=payload.sub,
        store_ids=set(payload.stores),
        token=token,
        user_id=str(session.user_id),
        session_id=str(session.id),
    )


def get_current_user_email(auth: AuthContext = Depends(get_auth_context)) -> str:
    """Backward-compatible helper to retrieve the authenticated email."""

    return auth.email


def assert_store_access(db: Session, auth: AuthContext, store_id: str) -> None:
    """Ensure that the user has access to the requested store."""

    if store_id not in auth.store_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Store access forbidden",
        )

    user = db.query(User).filter(User.id == auth.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    authorized_store_ids = {str(store.id) for store in user.stores}
    if store_id not in authorized_store_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Store access forbidden",
        )
