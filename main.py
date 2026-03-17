from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from db.database import Base, engine
from routers import auth, notes
from core.scheduler import start_scheduler

Base.metadata.create_all(bind=engine)

os.makedirs("uploads/avatars", exist_ok=True)

app = FastAPI(
    title="DevNote API",
    description="Backend API for the DevNote / Notes by Skillz application",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

app.include_router(auth.router)
app.include_router(notes.router)


@app.on_event("startup")
async def startup_event():
    start_scheduler()


@app.get("/", tags=["Health"])
def root():
    return {"status": "ok", "message": "DevNote API v2 is running"}


@app.get("/health", tags=["Health"])
def health():
    return {"status": "healthy"}

