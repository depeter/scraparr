"""Main FastAPI application"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from app.core.config import settings
from app.core.database import init_db
from app.services import scheduler_service
from app.api import scrapers, jobs, executions, proxy, database, websocket, auth, system

# Configure logging
logging.basicConfig(
    level=logging.INFO if settings.DEBUG else logging.WARNING,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    # Startup
    logger.info(f"Starting {settings.APP_NAME} v{settings.VERSION}")

    # Initialize database
    await init_db()
    logger.info("Database initialized")

    # Start scheduler
    scheduler_service.start()
    logger.info("Scheduler started")

    # Reload scheduled jobs
    await scheduler_service.reload_jobs()

    logger.info(f"{settings.APP_NAME} started successfully")

    yield

    # Shutdown
    logger.info("Shutting down...")
    scheduler_service.shutdown()
    logger.info("Scheduler stopped")


# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description="Advanced web scraping management system",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api")  # Auth routes are public
app.include_router(scrapers.router, prefix="/api")
app.include_router(jobs.router, prefix="/api")
app.include_router(executions.router, prefix="/api")
app.include_router(proxy.router, prefix="/api")
app.include_router(database.router)
app.include_router(websocket.router)
app.include_router(system.router, prefix="/api")


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": settings.APP_NAME,
        "version": settings.VERSION,
        "status": "running"
    }


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.BACKEND_HOST,
        port=settings.BACKEND_PORT,
        reload=settings.DEBUG
    )
