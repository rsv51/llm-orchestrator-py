"""
Chat completion API routes (OpenAI compatible).
"""
import time
import uuid
import json
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
from app.services.token_estimator import TokenEstimator
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
            # Handle streaming response with state tracking
            stream_state = {
                "last_chunk": None,
                "provider": None,
                "start_time": start_time,
                "accumulated_content": ""
            }
            
            async def tracked_stream():
                """Wrapper generator that tracks state for logging."""
                try:
                    async for chunk in router_service.route_streaming_request(
                        provider_name=provider_name,
                        request=request,
                        request_id=request_id,
                        api_key=api_key,
                        client_ip=client_ip
                    ):
                        # Track last chunk and accumulate content
                        if chunk.startswith("data: ") and not chunk.startswith("data: [DONE]"):
                            stream_state["last_chunk"] = chunk
                            # Extract content for token estimation
                            try:
                                data_str = chunk[6:].strip()
                                data = json.loads(data_str)
                                if "choices" in data and len(data["choices"]) > 0:
                                    delta = data["choices"][0].get("delta", {})
                                    content = delta.get("content", "")
                                    if content:
                                        stream_state["accumulated_content"] += content
                            except:
                                pass
                        yield chunk
                finally:
                    # Log after stream completes
                    from app.services.router import RequestRouter
                    from app.models.provider import Provider
                    from sqlalchemy import select
                    
                    try:
                        # Get provider info
                        query = select(Provider).where(Provider.name == provider_name, Provider.enabled == True)
                        result = await db.execute(query)
                        provider = result.scalar_one_or_none()
                        
                        if provider:
                            # Extract usage from last chunk or estimate
                            usage_info = None
                            if stream_state["last_chunk"]:
                                try:
                                    data_str = stream_state["last_chunk"][6:].strip()
                                    data = json.loads(data_str)
                                    if "usage" in data and data["usage"] and data["usage"].get("total_tokens", 0) > 0:
                                        # Provider returned usage info
                                        usage_info = data["usage"]
                                        logger.info(
                                            f"Extracted usage from provider: prompt={usage_info.get('prompt_tokens')}, "
                                            f"completion={usage_info.get('completion_tokens')}, "
                                            f"total={usage_info.get('total_tokens')}"
                                        )
                                    else:
                                        # Provider doesn't support usage tracking, estimate tokens
                                        logger.warning(f"Provider doesn't return usage info, estimating tokens")
                                        
                                        # Estimate tokens
                                        prompt_tokens = TokenEstimator.estimate_messages_tokens(request.messages)
                                        completion_tokens = TokenEstimator.estimate_completion_tokens(
                                            stream_state["accumulated_content"]
                                        )
                                        total_tokens = prompt_tokens + completion_tokens
                                        
                                        usage_info = {
                                            "prompt_tokens": prompt_tokens,
                                            "completion_tokens": completion_tokens,
                                            "total_tokens": total_tokens
                                        }
                                        
                                        logger.info(
                                            f"Estimated usage: prompt={prompt_tokens}, "
                                            f"completion={completion_tokens}, "
                                            f"total={total_tokens} (content_length={len(stream_state['accumulated_content'])})"
                                        )
                                except Exception as e:
                                    logger.error(f"Failed to extract/estimate usage: {str(e)}, chunk: {stream_state['last_chunk'][:200] if stream_state['last_chunk'] else 'None'}")
                            
                            # Create log entry
                            from app.models.request_log import RequestLog
                            latency_ms = int((time.time() - stream_state["start_time"]) * 1000)
                            log_entry = RequestLog(
                                provider_id=provider.id,
                                model=request.model,
                                endpoint="/v1/chat/completions",
                                method="POST",
                                status_code=200,
                                prompt_tokens=usage_info.get("prompt_tokens") if usage_info else None,
                                completion_tokens=usage_info.get("completion_tokens") if usage_info else None,
                                total_tokens=usage_info.get("total_tokens") if usage_info else None,
                                latency_ms=latency_ms,
                                user_id=api_key,
                                ip_address=client_ip
                            )
                            db.add(log_entry)
                            await db.commit()
                            
                            logger.info(
                                f"Streaming logged: tokens={usage_info.get('total_tokens') if usage_info else 0}"
                            )
                    except Exception as e:
                        logger.error(f"Failed to log streaming request: {str(e)}")
                        await db.rollback()
            
            return StreamingResponse(
                tracked_stream(),
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