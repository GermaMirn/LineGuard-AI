from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional
from datetime import datetime
from uuid import UUID
from app.models import UserRole

class UserBase(BaseModel):
    email: EmailStr
    role: Optional[UserRole] = UserRole.USER

class UserCreate(UserBase):
    password: str
    confirm_password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    role: Optional[UserRole] = None

class UserResponse(UserBase):
    uuid: UUID
    is_active: bool
    is_verified: bool
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True

class UserListResponse(BaseModel):
    users: list[UserResponse]

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user_uuid: str

class RefreshTokenRequest(BaseModel):
    refresh_token: str

class PasswordReset(BaseModel):
    email: EmailStr

class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str
    confirm_password: str

class RoleUpdate(BaseModel):
    role: str

    @field_validator('role')
    @classmethod
    def validate_role(cls, v):
        if v.upper() not in ['USER', 'ADMIN']:
            raise ValueError('Role must be USER or ADMIN')
        return v.upper()

