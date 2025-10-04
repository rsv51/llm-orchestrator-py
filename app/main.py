"""
Main FastAPI application entry point.
"""
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from app.core.config import settings
from app.core.database import init_db
from app.core.logger import get_logger
from app.api.middleware import setup_middleware
from app.api.routes import chat, models, admin, excel

logger = get_logger(__name__)


# ============================================================================
# Application Lifespan
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """
    Application lifespan manager.
    
    Handles startup and shutdown events.
    """
    # Startup
    logger.info("Starting LLM Orchestrator API")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Debug mode: {settings.debug}")
    
    # Initialize database
    try:
        await init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {str(e)}", exc_info=True)
        raise
    
    # Start health check service as background task
    health_check_task = None
    if settings.health_check_enabled:
        from app.services.health_check import start_health_check_service
        import asyncio
        health_check_task = asyncio.create_task(start_health_check_service())
        logger.info("Health check service started")
    
    logger.info("Application startup complete")
    
    yield
    
    # Shutdown
    logger.info("Shutting down LLM Orchestrator API")
    
    # Cancel health check task
    if settings.health_check_enabled and health_check_task is not None:
        health_check_task.cancel()
        try:
            await health_check_task
        except asyncio.CancelledError:
            logger.info("Health check service stopped")


# ============================================================================
# Application Factory
# ============================================================================

def create_app() -> FastAPI:
    """
    Create and configure FastAPI application.
    
    Returns:
        Configured FastAPI application instance
    """
    app = FastAPI(
        title=settings.app_name,
        description="Enterprise-grade multi-provider LLM API orchestration service",
        version="1.0.0",
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
        openapi_url="/openapi.json" if settings.debug else None,
        lifespan=lifespan
    )
    
    # Setup middleware
    setup_middleware(app)
    
    # Include admin and excel routers with /api prefix (internal use only)
    app.include_router(admin.router, prefix="/api")
    app.include_router(excel.router, prefix="/api")
    
    # Include chat and models routers twice for dual access:
    # 1. With /api prefix for admin UI compatibility
    app.include_router(chat.router, prefix="/api", tags=["admin-chat"])
    app.include_router(models.router, prefix="/api", tags=["admin-models"])
    
    # 2. Without prefix for OpenAI-compatible endpoints (/v1/chat/completions, /v1/models)
    app.include_router(chat.router, tags=["openai-chat"])
    app.include_router(models.router, tags=["openai-models"])
    
    # Mount static files for web UI
    web_dir = Path(__file__).parent.parent / "web"
    if web_dir.exists():
        app.mount("/admin-ui", StaticFiles(directory=str(web_dir), html=True), name="web")
        logger.info("Web UI mounted at /admin-ui")
    
    logger.info("Routes registered")
    
    return app


# ============================================================================
# Application Instance
# ============================================================================

app = create_app()


# ============================================================================
# Root Endpoints
# ============================================================================

@app.get("/", tags=["root"])
async def root():
    """Root endpoint - redirects to Web UI."""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/admin-ui/login.html")


@app.get("/api", tags=["root"])
@app.get("/api/", tags=["root"])
async def api_info():
    """API information endpoint."""
    return {
        "name": settings.app_name,
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs" if settings.debug else "disabled",
        "web_ui": "/admin-ui/",
    }


@app.get("/health", tags=["root"])
@app.get("/healthz", tags=["root"])
async def health_check():
    """Health check endpoint for load balancers."""
    return {
        "status": "healthy",
        "service": settings.app_name
    }


@app.get("/version", tags=["root"])
async def version():
    """Version information."""
    return {
        "version": "1.0.0",
        "api_version": "v1",
        "environment": settings.environment
    }


# ============================================================================
# Error Handlers
# ============================================================================

@app.exception_handler(404)
async def not_found_handler(request, exc):
    """Handle 404 errors."""
    return JSONResponse(
        status_code=404,
        content={
            "error": {
                "code": "not_found",
                "message": "The requested resource was not found",
                "path": str(request.url.path)
            }
        }
    )


@app.exception_handler(405)
async def method_not_allowed_handler(request, exc):
    """Handle 405 errors."""
    return JSONResponse(
        status_code=405,
        content={
            "error": {
                "code": "method_not_allowed",
                "message": f"Method {request.method} not allowed for this endpoint",
                "path": str(request.url.path)
            }
        }
    )


# ============================================================================
# Development Server
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
        access_log=True,
    )