"""
Chat completion API routes (OpenAI compatible).
"""
import time
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import (
    get_database,
    get_cache,
    get_client_ip,
    verify_api_key,
    get_rate_limiter
)
from app.api.schemas import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatCompletionChoice,
    ChatMessage,
    Usage,
    ErrorResponse,
    ErrorDetail
)
from app.core.cache import RedisCache
from app.core.logger import get_logger
from app.services.router import RequestRouter
from app.services.balancer import LoadBalancer
from app.models.request_log import RequestLog

logger = get_logger(__name__)

router = APIRouter(prefix="/v1/chat", tags=["chat"])


# ============================================================================
# Chat Completion Endpoint
# ============================================================================

@router.post(
    "/completions",
    response_model=ChatCompletionResponse,
    responses={
        401: {"model": ErrorResponse},
        429: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
    dependencies=[Depends(get_rate_limiter(60))]
)
async def create_chat_completion(
    request: ChatCompletionRequest,
    http_request: Request,
    db: AsyncSession = Depends(get_database),
    cache: RedisCache = Depends(get_cache),
    api_key: str = Depends(verify_api_key),
    client_ip: Optional[str] = Depends(get_client_ip)
):
    """
    Create a chat completion (OpenAI compatible).
    
    This endpoint accepts OpenAI-compatible chat completion requests and routes
    them to the appropriate LLM provider based on configuration and availability.
    
    **Features:**
    - Automatic provider selection and load balancing
    - Intelligent failover on errors
    - Token usage tracking and cost calculation
    - Request/response logging
    - Streaming support
    - Rate limiting
    
    **Custom Parameters:**
    - `provider`: Force specific provider (overrides auto-routing)
    - `fallback_providers`: Ordered list of fallback providers
    - `timeout`: Request timeout in seconds
    - `retry_count`: Number of retry attempts (0-5)
    """
    start_time = time.time()
    request_id = str(uuid.uuid4())
    
    logger.info(
        "Chat completion request received",
        extra={
            "request_id": request_id,
            "model": request.model,
            "stream": request.stream,
            "provider": request.provider,
            "api_key": api_key[:8] + "..." if api_key else None
        }
    )
    
    try:
        # Initialize router and balancer
        router_service = RequestRouter(db, cache)
        balancer = LoadBalancer(db, cache)
        
        # Select provider
        if request.provider:
            # Use specified provider
            provider_name = request.provider
            logger.info(f"Using specified provider: {provider_name}")
        else:
            # Use load balancer to select provider
            provider_name = await balancer.select_provider(
                model=request.model,
                fallback_providers=request.fallback_providers
            )
            logger.info(f"Load balancer selected provider: {provider_name}")
        
        # Route request to provider with failover support
        if request.stream:
            # Handle streaming response
            return StreamingResponse(
                router_service.route_streaming_request(
                    provider_name=provider_name,
                    request=request,
                    request_id=request_id,
                    api_key=api_key,
                    client_ip=client_ip
                ),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Request-ID": request_id
                }
            )
        else:
            # Handle non-streaming response with failover
            response = await router_service.route_request(
                provider_name=provider_name,
                request=request,
                request_id=request_id,
                api_key=api_key,
                client_ip=client_ip,
                fallback_providers=request.fallback_providers
            )
            
            # Calculate latency
            latency_ms = int((time.time() - start_time) * 1000)
            response.latency_ms = latency_ms
            
            logger.info(
                "Chat completion completed",
                extra={
                    "request_id": request_id,
                    "provider": response.provider,
                    "latency_ms": latency_ms,
                    "tokens": response.usage.total_tokens if response.usage else None
                }
            )
            
            return response
    
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    
    except Exception as e:
        logger.error(
            f"Chat completion failed: {str(e)}",
            extra={
                "request_id": request_id,
                "error": str(e),
                "model": request.model
            },
            exc_info=True
        )
        
        # Log failed request
        try:
            log_entry = RequestLog(
                provider_id=None,
                model=request.model,
                endpoint="/v1/chat/completions",
                method="POST",
                status_code=500,
                error_message=str(e),
                user_id=api_key,
                ip_address=client_ip,
                latency_ms=int((time.time() - start_time) * 1000)
            )
            db.add(log_entry)
            await db.commit()
        except Exception as log_error:
            logger.error(f"Failed to log request: {str(log_error)}")
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error=ErrorDetail(
                    code="internal_error",
                    message=str(e),
                    details={"request_id": request_id}
                ),
                request_id=request_id
            ).dict()
        )


# ============================================================================
# Legacy Completions Endpoint (for compatibility)
# ============================================================================

@router.post(
    "/text/completions",
    response_model=ChatCompletionResponse,
    deprecated=True,
    dependencies=[Depends(get_rate_limiter(60))]
)
async def create_text_completion(
    request: ChatCompletionRequest,
    http_request: Request,
    db: AsyncSession = Depends(get_database),
    cache: RedisCache = Depends(get_cache),
    api_key: str = Depends(verify_api_key),
    client_ip: Optional[str] = Depends(get_client_ip)
):
    """
    Legacy text completion endpoint (deprecated).
    
    This endpoint is deprecated. Please use `/v1/chat/completions` instead.
    """
    logger.warning(
        "Legacy text completion endpoint called",
        extra={"api_key": api_key[:8] + "..." if api_key else None}
    )
    
    # Forward to main chat completion endpoint
    return await create_chat_completion(
        request=request,
        http_request=http_request,
        db=db,
        cache=cache,
        api_key=api_key,
        client_ip=client_ip
    )