from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, EmailStr
from typing import List, Optional


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserSummary(BaseModel):
    id: str
    email: EmailStr
    created_at: datetime


class StoreSummary(BaseModel):
    id: str
    name: str


class SessionMetadata(BaseModel):
    id: str
    issued_at: datetime
    expires_at: datetime
    last_activity_at: Optional[datetime] = None
    store_scope: List[str]
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None


class LoginResponse(BaseModel):
    token: str
    user: UserSummary
    stores: List[StoreSummary]


class MeResponse(BaseModel):
    user: UserSummary
    stores: List[StoreSummary]
    session: Optional[SessionMetadata] = None
