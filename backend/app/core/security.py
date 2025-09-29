from datetime import datetime, timedelta, timezone
from typing import Optional, Sequence

from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, ValidationError

from .config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class TokenPayload(BaseModel):
    """Validated representation of the JWT payload."""

    sub: str
    exp: int
    stores: list[str] = []


def create_access_token(
    email: str,
    stores: Optional[Sequence[str]] = None,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Encode an access token with the configured expiry window."""

    lifetime = expires_delta or timedelta(minutes=settings.jwt_expire_minutes)
    expire_at = datetime.now(timezone.utc) + lifetime

    to_encode = {
        "sub": email,
        "stores": list(stores) if stores is not None else [],
        "exp": expire_at,
    }

    return jwt.encode(to_encode, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def verify_token(token: str) -> Optional[TokenPayload]:
    """Decode and validate a JWT, returning the typed payload when valid."""

    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
            options={"require": ["sub", "exp"]},
        )
        return TokenPayload(**payload)
    except (JWTError, ValidationError):
        return None


def verify_password(plain_password: str, hashed_password: str):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str):
    return pwd_context.hash(password)
