from typing import Optional

from fastapi import Header, HTTPException, status
from sqlalchemy.orm import Session

from ..models.models import User
from .security import verify_token


def get_current_user_email(authorization: Optional[str] = Header(None)) -> str:
    """Extract and validate the current user's email from the Authorization header."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header required",
        )

    token = authorization.split(" ", 1)[1].strip()
    email = verify_token(token)
    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    return email


def assert_store_access(db: Session, user_email: str, store_id: str) -> None:
    """Ensure that the user has access to the requested store."""
    user = db.query(User).filter(User.email == user_email).first()
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
