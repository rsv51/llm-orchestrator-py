"""
FastAPI dependencies for dependency injection.
"""
from typing import AsyncGenerator, Optional
from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.cache import RedisCache
from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger(__name__)


# ============================================================================
# Database Dependency
# ============================================================================

async def get_database() -> AsyncGenerator[AsyncSession, None]:
    """Get database session dependency."""
    async for session in get_db():
        yield session


# ============================================================================
# Cache Dependency
# ============================================================================

async def get_cache() -> RedisCache:
    """Get Redis cache dependency."""
    return RedisCache()


# ============================================================================
# Authentication Dependencies
# ============================================================================

async def verify_api_key(
    authorization: Optional[str] = Header(None),
    x_api_key: Optional[str] = Header(None)
) -> str:
    """
    Verify API key from Authorization header or X-API-Key header.
    
    Args:
        authorization: Authorization header value
        x_api_key: X-API-Key header value
        
    Returns:
        Validated API key
        
    Raises:
        HTTPException: If API key is missing or invalid
    """
    api_key = None
    
    # Try Authorization header first (Bearer token)
    if authorization:
        parts = authorization.split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            api_key = parts[1]
    
    # Fall back to X-API-Key header
    if not api_key and x_api_key:
        api_key = x_api_key
    
    if not api_key:
        logger.warning("API key missing in request")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key is required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Validate API key (in production, this should check against a database)
    # For now, we'll validate against configured keys
    if settings.api_keys and api_key not in settings.api_keys:
        logger.warning(f"Invalid API key attempted: {api_key[:8]}...")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return api_key


async def get_optional_api_key(
    authorization: Optional[str] = Header(None),
    x_api_key: Optional[str] = Header(None)
) -> Optional[str]:
    """
    Get optional API key (doesn't raise error if missing).
    
    Args:
        authorization: Authorization header value
        x_api_key: X-API-Key header value
        
    Returns:
        API key if present, None otherwise
    """
    try:
        return await verify_api_key(authorization, x_api_key)
    except HTTPException:
        return None


# ============================================================================
# Admin Authentication Dependency
# ============================================================================

async def verify_admin_key(
    authorization: Optional[str] = Header(None),
    x_admin_key: Optional[str] = Header(None)
) -> str:
    """
    Verify admin API key for management endpoints.
    
    Args:
        authorization: Authorization header value
        x_admin_key: X-Admin-Key header value
        
    Returns:
        Validated admin key
        
    Raises:
        HTTPException: If admin key is missing or invalid
    """
    admin_key = None
    
    # Try Authorization header first
    if authorization:
        parts = authorization.split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            admin_key = parts[1]
    
    # Fall back to X-Admin-Key header
    if not admin_key and x_admin_key:
        admin_key = x_admin_key
    
    if not admin_key:
        logger.warning("Admin key missing in request")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin key is required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Validate admin key
    if admin_key != settings.admin_key:
        logger.warning(f"Invalid admin key attempted: {admin_key[:min(8, len(admin_key))]}...")
        logger.debug(f"Expected admin key starts with: {settings.admin_key[:min(8, len(settings.admin_key))]}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid admin key",
        )
    
    return admin_key


# ============================================================================
# Request Context Dependencies
# ============================================================================

async def get_client_ip(
    x_forwarded_for: Optional[str] = Header(None),
    x_real_ip: Optional[str] = Header(None),
) -> Optional[str]:
    """
    Get client IP address from headers.
    
    Args:
        x_forwarded_for: X-Forwarded-For header value
        x_real_ip: X-Real-IP header value
        
    Returns:
        Client IP address
    """
    # Try X-Forwarded-For first (may contain multiple IPs)
    if x_forwarded_for:
        # Get the first IP in the chain (original client)
        return x_forwarded_for.split(",")[0].strip()
    
    # Fall back to X-Real-IP
    if x_real_ip:
        return x_real_ip.strip()
    
    return None


async def get_user_agent(
    user_agent: Optional[str] = Header(None)
) -> Optional[str]:
    """
    Get user agent from headers.
    
    Args:
        user_agent: User-Agent header value
        
    Returns:
        User agent string
    """
    return user_agent


# ============================================================================
# Rate Limiting Dependency
# ============================================================================

class RateLimiter:
    """Rate limiter for API endpoints."""
    
    def __init__(self, requests_per_minute: int = 60):
        self.requests_per_minute = requests_per_minute
    
    async def __call__(
        self,
        api_key: str = Depends(verify_api_key),
        cache: RedisCache = Depends(get_cache),
        client_ip: Optional[str] = Depends(get_client_ip)
    ) -> None:
        """
        Check rate limit for the given API key or IP.
        
        Args:
            api_key: API key from authentication
            cache: Redis cache instance
            client_ip: Client IP address
            
        Raises:
            HTTPException: If rate limit exceeded
        """
        # Use API key as primary identifier, fall back to IP
        identifier = api_key or client_ip or "unknown"
        
        # Rate limit key
        key = f"rate_limit:{identifier}"
        
        # Get current count
        count = await cache.get(key)
        
        if count is None:
            # First request in this minute
            await cache.set(key, 1, ttl=60)
        elif int(count) >= self.requests_per_minute:
            # Rate limit exceeded
            logger.warning(
                f"Rate limit exceeded for {identifier}",
                extra={"identifier": identifier, "count": count}
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Maximum {self.requests_per_minute} requests per minute.",
                headers={"Retry-After": "60"}
            )
        else:
            # Increment counter
            await cache.increment(key)


# ============================================================================
# Common Dependencies
# ============================================================================

def get_rate_limiter(requests_per_minute: int = 60) -> RateLimiter:
    """
    Get rate limiter with specified limit.
    
    Args:
        requests_per_minute: Maximum requests per minute
        
    Returns:
        RateLimiter instance
    """
    return RateLimiter(requests_per_minute=requests_per_minute)