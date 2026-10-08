"""
backend/main.py - CampusAI FastAPI Backend Entrypoint

Initializes FastAPI application, mounts CORS middleware, configures request logging,
includes API routers, and performs startup environment validation checks.
"""

import time
from datetime import datetime, timezone
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from backend.config import settings
from backend.api import chat, voice
from backend.utils.logger import get_logger

logger = get_logger("campusai.main")

# Track server start time for health uptime calculation
SERVER_START_TIME = time.time()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Lifespan context manager for startup and shutdown actions."""
    logger.info("Starting CampusAI Backend Server...")
    logger.info("Target College: %s", settings.COLLEGE_NAME)
    
    # Startup check: Validate Groq API Key
    try:
        settings.validate(require_groq_key=True)
        logger.info("Groq API Key configuration validated.")
    except Exception as err:
        logger.error("Startup Configuration Error: %s", str(err))

    yield
    logger.info("Shutting down CampusAI Backend Server...")


# FastAPI Application Instance
app = FastAPI(
    title="CampusAI Reception Robot Server",
    description="Backend API Server for CampusAI stationary college reception robot",
    version="1.0.0",
    lifespan=lifespan
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests_middleware(request: Request, call_next):
    """Log incoming HTTP requests and processing time."""
    start_time = time.time()
    response = await call_next(request)
    process_time_ms = (time.time() - start_time) * 1000.0
    logger.info(
        "%s %s -> Status %d (%.2f ms)",
        request.method, request.url.path, response.status_code, process_time_ms
    )
    return response


# Include Routers
app.include_router(chat.router)
app.include_router(voice.router)


@app.get("/health", tags=["System"])
async def health_check():
    """
    Health check endpoint returning system status, configured LLM model, uptime, and timestamp.
    """
    uptime_sec = round(time.time() - SERVER_START_TIME, 2)
    return {
        "status": "ok",
        "college": settings.COLLEGE_NAME,
        "model": settings.GROQ_LLM_MODEL,
        "uptime_seconds": uptime_sec,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }



if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=True
    )
