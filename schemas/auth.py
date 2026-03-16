from typing import Optional
from pydantic import BaseModel, EmailStr


class SignUpRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: int
    email: str
    full_name: Optional[str]
    avatar_url: Optional[str]
    bio: Optional[str]

    class Config:
        from_attributes = True


class ProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    bio: Optional[str] = None


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str
