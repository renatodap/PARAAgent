"""FastAPI application entry point for PARA Autopilot."""

from fastapi import FastAPI, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from auth import get_current_user
from config import settings
from contextlib import asynccontextmanager
import logging

# Import routers
from routers import para, tasks, weekly_review, search, integrations, beta, files, capture, oauth, google_services

# Import background jobs
from jobs.scheduler import start_scheduler, shutdown_scheduler

# Import monitoring
from monitoring.sentry_config import init_sentry, capture_exception

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Sentry
init_sentry()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    logger.info("Starting PARA Autopilot API")
    try:
        start_scheduler()
        logger.info("Background scheduler started successfully")
    except Exception as e:
        logger.error(f"Failed to start scheduler: {str(e)}")

    yield

    # Shutdown
    logger.info("Shutting down PARA Autopilot API")
    try:
        shutdown_scheduler()
        logger.info("Background scheduler stopped")
    except Exception as e:
        logger.error(f"Failed to stop scheduler: {str(e)}")

app = FastAPI(
    title="PARA Autopilot API",
    description="AI-powered personal productivity system using the PARA method",
    version="0.1.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL, "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch all unhandled exceptions and report to Sentry"""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)

    # Capture exception in Sentry
    capture_exception(exc, context={
        "url": str(request.url),
        "method": request.method,
        "client": request.client.host if request.client else None
    })

    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": str(exc) if settings.ENVIRONMENT == "development" else "An unexpected error occurred"
        }
    )

# Include routers
app.include_router(capture.router, prefix="/api/capture", tags=["Quick Capture"])
app.include_router(oauth.router, prefix="/api/oauth", tags=["OAuth2"])
app.include_router(google_services.router, prefix="/api/google", tags=["Google Services"])
app.include_router(para.router, prefix="/api/para", tags=["PARA"])
app.include_router(tasks.router, prefix="/api/tasks", tags=["Tasks"])
app.include_router(weekly_review.router, prefix="/api/review", tags=["Weekly Review"])
app.include_router(search.router, prefix="/api/search", tags=["Search"])
app.include_router(integrations.router, prefix="/api/integrations", tags=["Integrations"])
app.include_router(beta.router, prefix="/api/beta", tags=["Beta Waitlist"])
app.include_router(files.router, prefix="/api/files", tags=["File Management"])


@app.get("/")
def root():
    """Root endpoint."""
    return {
        "message": "PARA Autopilot API",
        "version": "0.1.0",
        "status": "active"
    }


@app.get("/api/health")
def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "environment": settings.ENVIRONMENT,
        "model": settings.CLAUDE_MODEL
    }


@app.get("/api/me")
async def get_current_user_info(user: dict = Depends(get_current_user)):
    """Get current authenticated user info."""
    return {
        "user_id": user.id,
        "email": user.email,
        "metadata": user.user_metadata
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
