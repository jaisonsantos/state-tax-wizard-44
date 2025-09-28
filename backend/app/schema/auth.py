from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, EmailStr
from typing import List


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


class LoginResponse(BaseModel):
    token: str
    user: UserSummary
    stores: List[StoreSummary]


class MeResponse(BaseModel):
    user: UserSummary
    stores: List[StoreSummary]
