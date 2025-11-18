from pydantic import BaseModel, EmailStr
from typing import Optional
from enum import Enum

class UserRole(str, Enum):
    USER = "USER"
    ADMIN = "ADMIN"

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    confirm_password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None

class UserResponse(BaseModel):
    uuid: str
    email: str
    role: str

class UserListResponse(BaseModel):
    users: list[UserResponse]

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    expires_in: int
    user_uuid: str

class RefreshTokenRequest(BaseModel):
    refresh_token: str

class RoleUpdate(BaseModel):
    role: UserRole

