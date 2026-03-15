from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from db.database import Base, engine
from routers import auth, notes

# Create all tables on startup
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="DevNote API",
    description="Backend API for the DevNote / Notes by Skillz application",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS — update origins for production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Replace with your frontend URL in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth.router)
app.include_router(notes.router)


@app.get("/", tags=["Health"])
def root():
    return {"status": "ok", "message": "DevNote API is running"}


@app.get("/health", tags=["Health"])
def health():
    return {"status": "healthy"}
