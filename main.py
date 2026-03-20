from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
import os

from db.database import Base, engine
from routers import auth, notes
from core.scheduler import start_scheduler
from core.limiter import limiter, rate_limit_exceeded_handler

Base.metadata.create_all(bind=engine)
os.makedirs("uploads/avatars", exist_ok=True)

app = FastAPI(
    title="Quill API",
    description="Backend API for Quill — Notes application",
    version="3.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://quillnote.netlify.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

app.include_router(auth.router)
app.include_router(notes.router)


@app.on_event("startup")
async def startup_event():
    start_scheduler()


@app.get("/", tags=["Health"])
def root():
    return {"status": "ok", "message": "Quill API v3 is running"}


@app.get("/health", tags=["Health"])
def health():
    return {"status": "healthy"}

