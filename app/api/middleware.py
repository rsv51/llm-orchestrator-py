"""
FastAPI middleware for logging, error handling, and CORS.
"""
import time
import uuid
from typing import Callable

from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware

from app.core.logger import get_logger
from app.core.config import settings

logger = get_logger(__name__)


# ============================================================================
# Request Logging Middleware
# ============================================================================

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log all incoming requests and responses."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and log details.
        
        Args:
            request: Incoming request
            call_next: Next middleware/endpoint
            
        Returns:
            Response from endpoint
        """
        # Generate request ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # Start timer
        start_time = time.time()
        
        # Log request
        logger.info(
            "Request started",
            extra={
                "request_id": request_id,
                "method": request.method,
                "url": str(request.url),
                "client_ip": request.client.host if request.client else None,
                "user_agent": request.headers.get("user-agent"),
            }
        )
        
        try:
            # Process request
            response = await call_next(request)
            
            # Calculate duration
            duration_ms = int((time.time() - start_time) * 1000)
            
            # Log response
            logger.info(
                "Request completed",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "url": str(request.url),
                    "status_code": response.status_code,
                    "duration_ms": duration_ms,
                }
            )
            
            # Add headers
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Process-Time"] = str(duration_ms)
            
            return response
        
        except Exception as e:
            # Calculate duration
            duration_ms = int((time.time() - start_time) * 1000)
            
            # Log error
            logger.error(
                "Request failed",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "url": str(request.url),
                    "error": str(e),
                    "duration_ms": duration_ms,
                },
                exc_info=True
            )
            
            # Re-raise to be handled by error handler
            raise


# ============================================================================
# Error Handling Middleware
# ============================================================================

class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """Middleware to handle uncaught exceptions."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and handle errors.
        
        Args:
            request: Incoming request
            call_next: Next middleware/endpoint
            
        Returns:
            Response from endpoint or error response
        """
        try:
            return await call_next(request)
        
        except Exception as e:
            # Get request ID if available
            request_id = getattr(request.state, "request_id", None)
            
            # Log error
            logger.error(
                f"Unhandled exception: {str(e)}",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "url": str(request.url),
                    "error_type": type(e).__name__,
                },
                exc_info=True
            )
            
            # Return error response
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "error": {
                        "code": "internal_error",
                        "message": "An internal error occurred",
                        "details": {
                            "request_id": request_id,
                            "type": type(e).__name__,
                        }
                    }
                },
                headers={
                    "X-Request-ID": request_id or "unknown"
                }
            )


# ============================================================================
# Rate Limit Middleware (Optional)
# ============================================================================

class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware to enforce rate limits globally.
    
    Note: This is a simple implementation. For production, consider using
    a more robust solution like slowapi or redis-based rate limiting.
    """
    
    def __init__(self, app, requests_per_minute: int = 60):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.request_counts = {}  # In-memory storage (not production-ready)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and check rate limit.
        
        Args:
            request: Incoming request
            call_next: Next middleware/endpoint
            
        Returns:
            Response from endpoint or rate limit error
        """
        # Skip rate limiting for health check endpoints
        if request.url.path in ["/health", "/healthz", "/"]:
            return await call_next(request)
        
        # Get client identifier
        client_id = request.client.host if request.client else "unknown"
        
        # Check rate limit (simplified - not production-ready)
        # In production, use Redis with sliding window or token bucket
        current_time = int(time.time() / 60)  # Current minute
        key = f"{client_id}:{current_time}"
        
        if key not in self.request_counts:
            self.request_counts[key] = 0
        
        self.request_counts[key] += 1
        
        if self.request_counts[key] > self.requests_per_minute:
            logger.warning(
                f"Rate limit exceeded for {client_id}",
                extra={
                    "client_id": client_id,
                    "count": self.request_counts[key],
                }
            )
            
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": {
                        "code": "rate_limit_exceeded",
                        "message": f"Rate limit exceeded. Maximum {self.requests_per_minute} requests per minute.",
                    }
                },
                headers={
                    "Retry-After": "60"
                }
            )
        
        return await call_next(request)


# ============================================================================
# CORS Configuration
# ============================================================================

def setup_cors(app):
    """
    Setup CORS middleware.
    
    Args:
        app: FastAPI application instance
    """
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID", "X-Process-Time"],
    )
    
    logger.info(
        "CORS configured",
        extra={"allowed_origins": settings.cors_origins}
    )


# ============================================================================
# Middleware Setup
# ============================================================================

def setup_middleware(app):
    """
    Setup all middleware for the application.
    
    Args:
        app: FastAPI application instance
    """
    # Add custom middleware (order matters - they wrap each other)
    # Outer middleware executes first on request, last on response
    
    # 1. Error handling (outermost - catches all errors)
    app.add_middleware(ErrorHandlingMiddleware)
    
    # 2. Request logging
    app.add_middleware(RequestLoggingMiddleware)
    
    # 3. Rate limiting (optional, can be disabled)
    if settings.enable_rate_limiting:
        app.add_middleware(
            RateLimitMiddleware,
            requests_per_minute=settings.rate_limit_per_minute
        )
        logger.info(
            "Rate limiting enabled",
            extra={"requests_per_minute": settings.rate_limit_per_minute}
        )
    
    # 4. CORS (innermost - closest to routes)
    setup_cors(app)
    
    logger.info("Middleware setup completed")