from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.config import settings
from app.database import engine, Base
from app.routers import auth, lectures, checkpoints, playback, misconceptions, dashboard, concepts, demo, workflow

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB tables
    Base.metadata.create_all(bind=engine)
    yield

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="MindTrace: An Intelligent Multimedia Learning Companion for Persistent Misconception Tracking (University FYP-1)",
    version="1.0.0",
    lifespan=lifespan
)

# CORS configuration for development and production
cors_origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Include Routers
app.include_router(auth.router, prefix=settings.API_V1_PREFIX)
app.include_router(lectures.router, prefix=settings.API_V1_PREFIX)
app.include_router(concepts.router, prefix=settings.API_V1_PREFIX)
app.include_router(checkpoints.router, prefix=settings.API_V1_PREFIX)
app.include_router(playback.router, prefix=settings.API_V1_PREFIX)
app.include_router(misconceptions.router, prefix=settings.API_V1_PREFIX)
app.include_router(dashboard.router, prefix=settings.API_V1_PREFIX)
app.include_router(demo.router, prefix=settings.API_V1_PREFIX)
app.include_router(workflow.router, prefix=settings.API_V1_PREFIX)
app.include_router(workflow.router, prefix="")

@app.get("/")
def root():
    return {
        "project": settings.PROJECT_NAME,
        "tagline": settings.PROJECT_TAGLINE,
        "version": "1.0.0 (FYP-1 Complete Working System)",
        "docs_url": "/docs",
        "api_prefix": settings.API_V1_PREFIX,
        "status": "online"
    }

@app.get("/health")
def health():
    return {"status": "healthy", "service": "MindTrace Backend API"}
