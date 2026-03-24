import os
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from PIL import Image

from db.database import get_db
from models.user import User
from models.session import UserSession
from schemas.auth import (
    SignUpRequest, LoginRequest, TokenResponse, UserResponse,
    ProfileUpdate, PasswordResetRequest, PasswordResetConfirm,
    ChangePasswordRequest, RefreshTokenRequest, AccessTokenResponse,
    ResendVerificationRequest, UserSessionResponse, LogoutSessionRequest,
)
from core.security import (
    hash_password, verify_password,
    create_access_token, create_refresh_token,
    decode_refresh_token, get_current_user,
    revoke_token, is_token_revoked,
)
from core.config import settings
from core.limiter import limiter

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

ACCESS_EXPIRE_SECONDS = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
VERIFICATION_TOKEN_EXPIRE_HOURS = 24


def _get_device_type(user_agent: str) -> str:
    """Extract device type from user agent string."""
    ua = user_agent.lower()
    if "mobile" in ua or "android" in ua or "iphone" in ua:
        return "mobile"
    elif "tablet" in ua or "ipad" in ua:
        return "tablet"
    else:
        return "desktop"


def _get_device_name(user_agent: str) -> str:
    """Extract a readable device name from user agent string."""
    ua = user_agent.lower()
    if "chrome" in ua and "edg" not in ua:
        return "Chrome"
    elif "firefox" in ua:
        return "Firefox"
    elif "safari" in ua and "chrome" not in ua:
        return "Safari"
    elif "edg" in ua:
        return "Edge"
    elif "opera" in ua:
        return "Opera"
    else:
        return "Unknown Browser"


def _issue_tokens(user: User, db: Session, device_info: dict = None) -> dict:
    """Issue a fresh access + refresh token pair for a user."""
    jti = str(uuid.uuid4())
    access_token = create_access_token({"sub": str(user.id), "jti": jti})
    refresh_token = create_refresh_token({"sub": str(user.id)})

    session = UserSession(
        user_id=user.id,
        hashed_refresh_token=hash_password(refresh_token),
        device_name=device_info.get("device_name") if device_info else None,
        device_type=device_info.get("device_type") if device_info else None,
        ip_address=device_info.get("ip_address") if device_info else None,
        user_agent=device_info.get("user_agent") if device_info else None,
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": ACCESS_EXPIRE_SECONDS,
        "session_id": session.id,
    }


async def _send_verification(user: User, db: Session):
    """Generate a verification token and send the email."""
    token = secrets.token_urlsafe(32)
    user.verification_token = token
    user.verification_token_expires = datetime.now(timezone.utc) + timedelta(
        hours=VERIFICATION_TOKEN_EXPIRE_HOURS
    )
    db.commit()
    try:
        from core.email import send_verification_email
        await send_verification_email(user.email, token, user.full_name)
    except Exception:
        pass  



@router.post("/signup", status_code=201)
@limiter.limit("10/minute")
async def sign_up(request: Request, payload: SignUpRequest, db: Session = Depends(get_db)):
    """
    Register a new account.
    - Creates the user as unverified
    - Sends a verification email
    - Returns a message (no tokens yet — user must verify first)
    """
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        is_verified=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    await _send_verification(user, db)

    return {
        "message": "Account created. Please check your email to verify your account.",
        "email": user.email,
    }



@router.get("/verify-email")
def verify_email(token: str, db: Session = Depends(get_db)):
    """
    Confirm email using the token from the verification link.
    Returns JSON response for frontend to handle.
    """
    user = db.query(User).filter(User.verification_token == token).first()

    if not user:
        raise HTTPException(
            status_code=400,
            detail="Invalid verification link. It may have already been used."
        )

    if not user.verification_token_expires:
        raise HTTPException(
            status_code=400,
            detail="Verification link is invalid."
        )

    expires = user.verification_token_expires
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)

    if datetime.now(timezone.utc) > expires:
        raise HTTPException(
            status_code=400,
            detail="Verification link has expired. Please request a new one."
        )

    user.is_verified = True
    user.verification_token = None
    user.verification_token_expires = None
    db.commit()

    return {"message": "Your email has been verified. You can now log in."}


@router.post("/resend-verification")
@limiter.limit("5/minute")
async def resend_verification(
    request: Request,
    payload: ResendVerificationRequest,
    db: Session = Depends(get_db),
):
    """Resend the verification email. Rate limited to prevent abuse."""
    user = db.query(User).filter(User.email == payload.email).first()

    if not user:
        return {"message": "If that email exists and is unverified, a new link has been sent."}

    if user.is_verified:
        raise HTTPException(status_code=400, detail="This account is already verified.")

    await _send_verification(user, db)
    return {"message": "If that email exists and is unverified, a new link has been sent."}



@router.post("/login", response_model=TokenResponse)
@limiter.limit("10/minute")
def login(request: Request, payload: LoginRequest, db: Session = Depends(get_db)):
    """
    Login with email and password.
    - Blocked if account is not verified
    - Returns access + refresh tokens on success
    """
    user = db.query(User).filter(User.email == payload.email, User.is_active == True).first()

    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not user.is_verified:
        raise HTTPException(
            status_code=403,
            detail="Email not verified. Please check your inbox or request a new verification link.",
        )

    device_info = {
        "ip_address": request.client.host if request.client else None,
        "user_agent": request.headers.get("user-agent"),
        "device_type": _get_device_type(request.headers.get("user-agent", "")),
        "device_name": _get_device_name(request.headers.get("user-agent", "")),
    }

    return _issue_tokens(user, db, device_info)



@router.post("/refresh", response_model=AccessTokenResponse)
@limiter.limit("30/minute")
def refresh_access_token(
    request: Request,
    payload: RefreshTokenRequest,
    db: Session = Depends(get_db),
):
    """Exchange a valid refresh token for a new access token (token rotation)."""
    token_data = decode_refresh_token(payload.refresh_token)
    user_id = token_data.get("sub")

    user = db.query(User).filter(User.id == int(user_id), User.is_active == True).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    if not user.hashed_refresh_token or not verify_password(
        payload.refresh_token, user.hashed_refresh_token
    ):
        user.hashed_refresh_token = None
        db.query(UserSession).filter(UserSession.user_id == user.id).update({"is_active": False})
        db.commit()
        raise HTTPException(
            status_code=401,
            detail="Refresh token reuse detected. Please log in again.",
        )

    tokens = _issue_tokens(user, db, {
        "ip_address": request.client.host if request.client else None,
        "user_agent": request.headers.get("user-agent"),
        "device_type": _get_device_type(request.headers.get("user-agent", "")),
        "device_name": _get_device_name(request.headers.get("user-agent", "")),
    })
    return {
        "access_token": tokens["access_token"],
        "token_type": "bearer",
        "expires_in": ACCESS_EXPIRE_SECONDS,
    }


@router.post("/logout")
def logout(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Logout — invalidates the current refresh token."""
    current_user.hashed_refresh_token = None
    db.query(UserSession).filter(UserSession.user_id == current_user.id).update({"is_active": False})
    db.commit()
    return {"message": "Logged out successfully"}


@router.post("/logout-all")
def logout_all_devices(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Logout from all devices by invalidating the refresh token."""
    current_user.hashed_refresh_token = None
    db.query(UserSession).filter(UserSession.user_id == current_user.id).update({"is_active": False})
    db.commit()
    return {"message": "Logged out from all devices"}


@router.get("/sessions", response_model=list[UserSessionResponse])
def get_user_sessions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get all active sessions for the current user."""
    sessions = db.query(UserSession).filter(
        UserSession.user_id == current_user.id,
        UserSession.is_active == True,
    ).order_by(UserSession.created_at.desc()).all()

    return [
        UserSessionResponse(
            id=session.id,
            device_name=session.device_name,
            device_type=session.device_type,
            ip_address=session.ip_address,
            user_agent=session.user_agent,
            is_active=session.is_active,
            last_used_at=session.last_used_at.isoformat() if session.last_used_at else None,
            created_at=session.created_at.isoformat(),
        )
        for session in sessions
    ]


@router.post("/sessions/{session_id}/logout")
def logout_session(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Logout from a specific session."""
    session = db.query(UserSession).filter(
        UserSession.id == session_id,
        UserSession.user_id == current_user.id,
    ).first()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    session.is_active = False
    db.commit()
    return {"message": "Session logged out successfully"}



@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.patch("/me", response_model=UserResponse)
def update_profile(
    payload: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if payload.full_name is not None:
        current_user.full_name = payload.full_name
    if payload.bio is not None:
        current_user.bio = payload.bio
    db.commit()
    db.refresh(current_user)
    return current_user


@router.post("/me/avatar", response_model=UserResponse)
@limiter.limit("10/minute")
async def upload_avatar(
    request: Request,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if file.content_type not in ("image/jpeg", "image/png"):
        raise HTTPException(status_code=400, detail="Only JPEG and PNG images are allowed")

    contents = await file.read()
    if len(contents) > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=400, detail="File size exceeds 5MB limit")

    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    filename = f"{uuid.uuid4()}.jpg"
    filepath = os.path.join(settings.UPLOAD_DIR, filename)

    from io import BytesIO
    img = Image.open(BytesIO(contents)).convert("RGB")
    img = img.resize((200, 200), Image.LANCZOS)
    img.save(filepath, "JPEG", quality=85)

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
    if not verify_password(payload.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    current_user.hashed_password = hash_password(payload.new_password)
    current_user.hashed_refresh_token = None  
    db.commit()
    return {"message": "Password changed. Please log in again."}




@router.post("/forgot-password")
@limiter.limit("5/minute")
async def forgot_password(
    request: Request,
    payload: PasswordResetRequest,
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.email == payload.email).first()
    if user and user.is_verified:
        token = secrets.token_urlsafe(32)
        user.reset_token = token
        user.reset_token_expires = datetime.now(timezone.utc) + timedelta(hours=1)
        db.commit()
        try:
            from core.email import send_password_reset_email
            await send_password_reset_email(user.email, token)
        except Exception:
            pass
    return {"message": "If that email exists, a reset link has been sent"}


@router.post("/reset-password")
def reset_password(payload: PasswordResetConfirm, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.reset_token == payload.token).first()
    if not user or not user.reset_token_expires:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    expires = user.reset_token_expires
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)

    if datetime.now(timezone.utc) > expires:
        raise HTTPException(status_code=400, detail="Reset token has expired")

    user.hashed_password = hash_password(payload.new_password)
    user.reset_token = None
    user.reset_token_expires = None
    user.hashed_refresh_token = None
    db.commit()
    return {"message": "Password reset successfully. Please log in."}




