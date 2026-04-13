from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://user:password@localhost:5432/devnote"
    SECRET_KEY: str = "change-this-in-production"
    ALGORITHM: str = "HS256"

    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    REFRESH_SECRET_KEY: str = "refresh-secret-change-in-production"

    REDIS_URL: str = "redis://localhost:6379"

    RATE_LIMIT_PER_MINUTE: int = 60
    AUTH_RATE_LIMIT_PER_MINUTE: int = 10

    BREVO_SMTP_USER: str = ""
    BREVO_SMTP_PASSWORD: str = ""

    UPLOAD_DIR: str = "uploads/avatars"
    MAX_UPLOAD_SIZE: int = 5_000_000  # 5MB

    BASE_URL: str = "http://localhost:8000"
    FRONTEND_URL: str = "http://localhost:3000"

    class Config:
        env_file = ".env"
        extra = "ignore"  
        case_sensitive = False


settings = Settings()
