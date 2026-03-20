from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer

from core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

TOKEN_TYPE_ACCESS = "access"
TOKEN_TYPE_REFRESH = "refresh"



def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)



def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    to_encode["type"] = TOKEN_TYPE_ACCESS
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode["exp"] = expire
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(data: dict) -> str:
    to_encode = data.copy()
    to_encode["type"] = TOKEN_TYPE_REFRESH
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode["exp"] = expire
    return jwt.encode(to_encode, settings.REFRESH_SECRET_KEY, algorithm=settings.ALGORITHM)



def decode_access_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if payload.get("type") != TOKEN_TYPE_ACCESS:
            raise HTTPException(status_code=401, detail="Invalid token type")
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


def decode_refresh_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, settings.REFRESH_SECRET_KEY, algorithms=[settings.ALGORITHM])
        if payload.get("type") != TOKEN_TYPE_REFRESH:
            raise HTTPException(status_code=401, detail="Invalid token type")
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )


def get_redis():
    """Get Redis client — falls back gracefully if Redis is unavailable."""
    try:
        import redis as redis_lib
        client = redis_lib.from_url(settings.REDIS_URL, decode_responses=True)
        client.ping()
        return client
    except Exception:
        return None


def revoke_token(jti: str, expires_in_seconds: int):
    """Add token JTI to Redis blocklist."""
    r = get_redis()
    if r:
        r.setex(f"revoked:{jti}", expires_in_seconds, "1")


def is_token_revoked(jti: str) -> bool:
    """Check if a token has been revoked."""
    r = get_redis()
    if r:
        return r.exists(f"revoked:{jti}") == 1
    return False  # fail open if Redis is down




from db.database import get_db
from sqlalchemy.orm import Session
from models.user import User


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    payload = decode_access_token(token)

    user_id: str = payload.get("sub")
    jti: str = payload.get("jti", "")

    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    if jti and is_token_revoked(jti):
        raise HTTPException(status_code=401, detail="Token has been revoked")

    user = db.query(User).filter(User.id == int(user_id), User.is_active == True).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found or deactivated")

    return user
