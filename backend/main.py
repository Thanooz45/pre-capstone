"""
main.py — FastAPI Application Entry Point
==========================================
Human Height Estimator — Capstone Project
Tech stack: FastAPI · OpenCV · YOLOv8 · MediaPipe · Pinhole Camera Geometry
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from api.routes import router
from core.config import settings
from core.logging_config import setup_logging

setup_logging()  # configure structured console logging


# ---------------------------------------------------------------------------
# Lifespan: load heavy models once on startup
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Pre-load YOLOv8 + MediaPipe models at startup so the first request
    is not slow."""
    from services.height_estimator import load_models
    load_models()
    yield
    # (cleanup if needed on shutdown)


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------
app = FastAPI(
    title=settings.PROJECT_NAME,
    description=(
        "Estimates real-world human height from a single image using:\n"
        "  • YOLOv8  — person detection\n"
        "  • MediaPipe Pose  — keypoint extraction\n"
        "  • Pinhole Camera Geometry  — pixel-to-cm conversion\n"
        "  • OpenCV  — image annotation"
    ),
    version=settings.VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")


@app.get("/", tags=["Health"])
def root():
    return {
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "ok"}
