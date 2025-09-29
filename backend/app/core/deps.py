from dataclasses import dataclass
from typing import Optional

from fastapi import Header, HTTPException, status
from sqlalchemy.orm import Session

from ..models.models import User
from .security import TokenPayload, verify_token


@dataclass
class AuthContext:
    """Represents the authenticated subject and authorized stores."""

    subject: str
    store_ids: set[str]
    token: str

    @property
    def email(self) -> str:
        return self.subject


def get_auth_context(authorization: Optional[str] = Header(None)) -> AuthContext:
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

    return AuthContext(subject=payload.sub, store_ids=set(payload.stores), token=token)


def get_current_user_email(authorization: Optional[str] = Header(None)) -> str:
    """Backward-compatible helper to retrieve the authenticated email."""

    return get_auth_context(authorization).email


def assert_store_access(db: Session, auth: AuthContext, store_id: str) -> None:
    """Ensure that the user has access to the requested store."""

    if store_id not in auth.store_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Store access forbidden",
        )

    user = db.query(User).filter(User.email == auth.email).first()
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
