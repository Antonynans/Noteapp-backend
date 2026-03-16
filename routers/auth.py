import os
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from PIL import Image

from db.database import get_db
from models.user import User
from schemas.auth import (
    SignUpRequest, LoginRequest, TokenResponse, UserResponse,
    ProfileUpdate, PasswordResetRequest, PasswordResetConfirm, ChangePasswordRequest
)
from core.security import hash_password, verify_password, create_access_token, get_current_user
from core.config import settings

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def sign_up(payload: SignUpRequest, db: Session = Depends(get_db)):
    """Register a new user account."""
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_access_token({"sub": str(user.id)})
    return {"access_token": token, "token_type": "bearer"}


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    """Log in with email and password."""
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = create_access_token({"sub": str(user.id)})
    return {"access_token": token, "token_type": "bearer"}


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """Get current authenticated user."""
    return current_user


@router.patch("/me", response_model=UserResponse)
def update_profile(
    payload: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update profile name and bio."""
    if payload.full_name is not None:
        current_user.full_name = payload.full_name
    if payload.bio is not None:
        current_user.bio = payload.bio
    db.commit()
    db.refresh(current_user)
    return current_user


@router.post("/me/avatar", response_model=UserResponse)
async def upload_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Upload a profile avatar image (JPEG or PNG, max 5MB)."""
    if file.content_type not in ("image/jpeg", "image/png"):
        raise HTTPException(status_code=400, detail="Only JPEG and PNG images are allowed")

    contents = await file.read()
    if len(contents) > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=400, detail="File size exceeds 5MB limit")

    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    filename = f"{uuid.uuid4()}.jpg"
    filepath = os.path.join(settings.UPLOAD_DIR, filename)

    # Resize to 200x200 and save
    from io import BytesIO
    img = Image.open(BytesIO(contents)).convert("RGB")
    img = img.resize((200, 200), Image.LANCZOS)
    img.save(filepath, "JPEG", quality=85)

    # Delete old avatar
    if current_user.avatar_url:
        old_path = current_user.avatar_url.lstrip("/")
        if os.path.exists(old_path):
            os.remove(old_path)

    current_user.avatar_url = f"/{filepath}"
    db.commit()
    db.refresh(current_user)
    return current_user


@router.post("/me/change-password")
def change_password(
    payload: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Change password while logged in."""
    if not verify_password(payload.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    current_user.hashed_password = hash_password(payload.new_password)
    db.commit()
    return {"message": "Password changed successfully"}


@router.post("/forgot-password")
async def forgot_password(payload: PasswordResetRequest, db: Session = Depends(get_db)):
    """Send a password reset email."""
    user = db.query(User).filter(User.email == payload.email).first()
    if user:
        token = secrets.token_urlsafe(32)
        user.reset_token = token
        user.reset_token_expires = datetime.now(timezone.utc) + timedelta(hours=1)
        db.commit()
        try:
            from core.email import send_password_reset_email
            await send_password_reset_email(user.email, token)
        except Exception:
            pass  # silently fail if email not configured
    # Always return success to prevent email enumeration
    return {"message": "If that email exists, a reset link has been sent"}


@router.post("/reset-password")
def reset_password(payload: PasswordResetConfirm, db: Session = Depends(get_db)):
    """Reset password using the token from the email."""
    user = db.query(User).filter(User.reset_token == payload.token).first()
    if not user or not user.reset_token_expires:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    if datetime.now(timezone.utc) > user.reset_token_expires.replace(tzinfo=timezone.utc):
        raise HTTPException(status_code=400, detail="Reset token has expired")

    user.hashed_password = hash_password(payload.new_password)
    user.reset_token = None
    user.reset_token_expires = None
    db.commit()
    return {"message": "Password reset successfully"}

