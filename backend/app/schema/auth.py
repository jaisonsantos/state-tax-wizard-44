from pydantic import BaseModel, EmailStr
from typing import List, Optional
from datetime import datetime
import uuid

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class LoginResponse(BaseModel):
    token: str
    user: "UserInfo"

class UserInfo(BaseModel):
    id: str
    email: str
    stores: List["StoreInfo"] = []

class StoreInfo(BaseModel):
    id: str
    platform: str
    domain: str
    country: str
    state: Optional[str] = None
    created_at: datetime