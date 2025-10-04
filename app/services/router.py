"""
Request router for handling LLM API requests with failover.
"""
import time
import asyncio
import json
from typing import Optional, AsyncGenerator, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import RedisCache
from app.core.logger import get_logger
from app.core.config import settings
from app.api.schemas import ChatCompletionRequest, ChatCompletionResponse
from app.providers.factory import ProviderFactory
from app.models.request_log import RequestLog
from app.models.provider import Provider
from sqlalchemy import select

logger = get_logger(__name__)


class RequestRouter:
    """
    Router for handling requests with intelligent failover.
    
    Features:
    - Automatic provider failover on errors
    - Request/response logging
    - Token usage tracking
    - Cost calculation
    """
    
    def __init__(self, db: AsyncSession, cache: RedisCache):
        """
        Initialize request router.
        
        Args:
            db: Database session
            cache: Redis cache instance
        """
        self.db = db
        self.cache = cache
        self.provider_factory = ProviderFactory()
    
    async def route_request(
        self,
        provider_name: str,
        request: ChatCompletionRequest,
        request_id: str,
        api_key: Optional[str] = None,
        client_ip: Optional[str] = None,
        fallback_providers: Optional[List[str]] = None
    ) -> ChatCompletionResponse:
        """
        Route request to provider with intelligent failover support.
        
        Tries the primary provider first, then automatically falls back to
        alternative providers if the primary fails.
        
        Args:
            provider_name: Primary provider name
            request: Chat completion request
            request_id: Unique request ID
            api_key: User API key
            client_ip: Client IP address
            fallback_providers: Ordered list of fallback provider names
            
        Returns:
            Chat completion response
            
        Raises:
            Exception: If all providers fail
        """
        start_time = time.time()
        
        # Build provider list: primary + fallbacks
        provider_names = [provider_name]
        if fallback_providers:
            provider_names.extend(fallback_providers)
        
        # Try each provider in sequence
        last_errors = {}
        for current_provider_name in provider_names:
            try:
                logger.info(
                    f"Attempting provider: {current_provider_name}",
                    extra={
                        "request_id": request_id,
                        "provider": current_provider_name,
                        "is_fallback": current_provider_name != provider_name
                    }
                )
                
                response = await self._try_provider(
                    provider_name=current_provider_name,
                    request=request,
                    request_id=request_id,
                    start_time=start_time,
                    api_key=api_key,
                    client_ip=client_ip
                )
                
                # Success! Add provider info and return
                response.provider = current_provider_name
                return response
            
            except Exception as e:
                last_errors[current_provider_name] = str(e)
                logger.warning(
                    f"Provider {current_provider_name} failed: {str(e)}",
                    extra={
                        "request_id": request_id,
                        "provider": current_provider_name,
                        "error": str(e)
                    }
                )
                # Continue to next provider
        
        # All providers failed
        error_summary = "; ".join([f"{name}: {err}" for name, err in last_errors.items()])
        logger.error(
            f"All providers failed for request {request_id}",
            extra={
                "request_id": request_id,
                "providers_tried": list(last_errors.keys()),
                "errors": last_errors
            }
        )
        
        raise Exception(f"All providers failed. Errors: {error_summary}")
    
    async def _try_provider(
        self,
        provider_name: str,
        request: ChatCompletionRequest,
        request_id: str,
        start_time: float,
        api_key: Optional[str],
        client_ip: Optional[str]
    ) -> ChatCompletionResponse:
        """
        Try a single provider with retries.
        
        Args:
            provider_name: Provider name
            request: Chat completion request
            request_id: Request ID
            start_time: Request start time
            api_key: User API key
            client_ip: Client IP
            
        Returns:
            Chat completion response
            
        Raises:
            Exception: If all retry attempts fail
        """
        retry_count = request.retry_count or settings.max_retry_count
        
        # Get provider from database
        provider = await self._get_provider(provider_name)
        if not provider:
            raise Exception(f"Provider {provider_name} not found or disabled")
        
        last_error = None
        
        # Try with retries (same provider, different attempts)
        for attempt in range(retry_count + 1):
            try:
                logger.debug(
                    f"Provider {provider_name} attempt {attempt + 1}/{retry_count + 1}",
                    extra={"request_id": request_id}
                )
                
                # Create provider instance
                provider_instance = self.provider_factory.create_provider(
                    provider_type=provider.type,
                    api_key=provider.api_key,
                    base_url=provider.base_url,
                    timeout=request.timeout or provider.timeout
                )
                
                # Send request
                response = await provider_instance.chat_completion(request)
                
                # Log successful request
                latency_ms = int((time.time() - start_time) * 1000)
                await self._log_request(
                    provider_id=provider.id,
                    request=request,
                    response=response,
                    latency_ms=latency_ms,
                    api_key=api_key,
                    client_ip=client_ip
                )
                
                return response
            
            except Exception as e:
                last_error = e
                logger.debug(
                    f"Attempt {attempt + 1} failed: {str(e)}",
                    extra={"request_id": request_id, "provider": provider_name}
                )
                
                # Wait before retry (exponential backoff)
                if attempt < retry_count:
                    wait_time = min(2 ** attempt, 10)  # Max 10 seconds
                    await asyncio.sleep(wait_time)
        
        # All retries failed for this provider
        latency_ms = int((time.time() - start_time) * 1000)
        await self._log_failed_request(
            provider_id=provider.id,
            request=request,
            error=str(last_error),
            latency_ms=latency_ms,
            api_key=api_key,
            client_ip=client_ip
        )
        
        raise Exception(f"Provider {provider_name} failed after {retry_count + 1} attempts: {str(last_error)}")
    
    async def route_streaming_request(
        self,
        provider_name: str,
        request: ChatCompletionRequest,
        request_id: str,
        api_key: Optional[str] = None,
        client_ip: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """
        Route streaming request to provider with Token usage tracking.
        
        Args:
            provider_name: Target provider name
            request: Chat completion request
            request_id: Unique request ID
            api_key: User API key
            client_ip: Client IP address
            
        Yields:
            Server-sent event chunks
        """
        start_time = time.time()
        
        # Get provider
        provider = await self._get_provider(provider_name)
        if not provider:
            raise Exception(f"Provider {provider_name} not found")
        
        # Track usage info from streaming response
        usage_info: Optional[Dict[str, Any]] = None
        
        try:
            # Create provider instance
            provider_instance = self.provider_factory.create_provider(
                provider_type=provider.type,
                api_key=provider.api_key,
                base_url=provider.base_url,
                timeout=request.timeout or provider.timeout
            )
            
            # Stream response and track last chunk for usage extraction
            last_chunk: Optional[str] = None
            
            async for chunk in provider_instance.chat_completion_stream(request):
                # Track the last valid chunk (not [DONE])
                if chunk.startswith("data: ") and not chunk.startswith("data: [DONE]"):
                    last_chunk = chunk
                
                yield chunk
            
            # Extract usage from the LAST chunk after streaming completes
            if last_chunk:
                try:
                    data_str = last_chunk[6:].strip()  # Remove "data: " prefix
                    data = json.loads(data_str)
                    
                    # Validate usage exists and has non-zero total_tokens
                    if "usage" in data:
                        usage = data["usage"]
                        if usage.get("total_tokens", 0) > 0:
                            usage_info = usage
                            logger.debug(
                                "Extracted usage from last chunk",
                                extra={
                                    "prompt_tokens": usage.get("prompt_tokens"),
                                    "completion_tokens": usage.get("completion_tokens"),
                                    "total_tokens": usage.get("total_tokens")
                                }
                            )
                except (json.JSONDecodeError, KeyError) as e:
                    logger.warning(f"Failed to extract usage from last chunk: {str(e)}")
            
            # Log successful streaming request with usage info
            latency_ms = int((time.time() - start_time) * 1000)
            await self._log_streaming_request(
                provider_id=provider.id,
                request=request,
                usage_info=usage_info,
                latency_ms=latency_ms,
                api_key=api_key,
                client_ip=client_ip
            )
        
        except Exception as e:
            logger.error(
                f"Streaming request failed on {provider_name}: {str(e)}",
                extra={
                    "request_id": request_id,
                    "provider": provider_name,
                    "error": str(e)
                }
            )
            
            # Log failed request
            latency_ms = int((time.time() - start_time) * 1000)
            await self._log_failed_request(
                provider_id=provider.id,
                request=request,
                error=str(e),
                latency_ms=latency_ms,
                api_key=api_key,
                client_ip=client_ip
            )
            
            raise
    
    async def _get_provider(self, provider_name: str) -> Optional[Provider]:
        """
        Get provider from database with caching.
        
        Args:
            provider_name: Provider name
            
        Returns:
            Provider instance or None
        """
        # Query database directly (caching Provider ORM objects is problematic)
        query = select(Provider).where(
            Provider.name == provider_name,
            Provider.enabled == True
        )
        result = await self.db.execute(query)
        provider = result.scalar_one_or_none()
        
        return provider
    
    async def _log_request(
        self,
        provider_id: int,
        request: ChatCompletionRequest,
        response: Optional[ChatCompletionResponse],
        latency_ms: int,
        api_key: Optional[str],
        client_ip: Optional[str]
    ):
        """
        Log successful request to database.
        
        Args:
            provider_id: Provider ID
            request: Request object
            response: Response object (None for streaming)
            latency_ms: Request latency in milliseconds
            api_key: User API key
            client_ip: Client IP address
        """
        try:
            log_entry = RequestLog(
                provider_id=provider_id,
                model=request.model,
                endpoint="/v1/chat/completions",
                method="POST",
                status_code=200,
                prompt_tokens=response.usage.prompt_tokens if response and response.usage else None,
                completion_tokens=response.usage.completion_tokens if response and response.usage else None,
                total_tokens=response.usage.total_tokens if response and response.usage else None,
                latency_ms=latency_ms,
                user_id=api_key,
                ip_address=client_ip
            )
            
            self.db.add(log_entry)
            await self.db.commit()
        
        except Exception as e:
            logger.error(f"Failed to log request: {str(e)}")
            await self.db.rollback()
    
    async def _log_streaming_request(
        self,
        provider_id: int,
        request: ChatCompletionRequest,
        usage_info: Optional[Dict[str, Any]],
        latency_ms: int,
        api_key: Optional[str],
        client_ip: Optional[str]
    ):
        """
        Log successful streaming request with Token usage.
        
        Args:
            provider_id: Provider ID
            request: Request object
            usage_info: Usage information from final chunk
            latency_ms: Request latency in milliseconds
            api_key: User API key
            client_ip: Client IP address
        """
        try:
            log_entry = RequestLog(
                provider_id=provider_id,
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
            
            self.db.add(log_entry)
            await self.db.commit()
            
            if usage_info:
                logger.debug(
                    "Streaming request logged with usage",
                    extra={
                        "prompt_tokens": usage_info.get("prompt_tokens"),
                        "completion_tokens": usage_info.get("completion_tokens"),
                        "total_tokens": usage_info.get("total_tokens")
                    }
                )
        
        except Exception as e:
            logger.error(f"Failed to log streaming request: {str(e)}")
            await self.db.rollback()
    
    async def _log_failed_request(
        self,
        provider_id: int,
        request: ChatCompletionRequest,
        error: str,
        latency_ms: int,
        api_key: Optional[str],
        client_ip: Optional[str]
    ):
        """
        Log failed request to database.
        
        Args:
            provider_id: Provider ID
            request: Request object
            error: Error message
            latency_ms: Request latency in milliseconds
            api_key: User API key
            client_ip: Client IP address
        """
        try:
            log_entry = RequestLog(
                provider_id=provider_id,
                model=request.model,
                endpoint="/v1/chat/completions",
                method="POST",
                status_code=500,
                error_message=error,
                latency_ms=latency_ms,
                user_id=api_key,
                ip_address=client_ip
            )
            
            self.db.add(log_entry)
            await self.db.commit()
        
        except Exception as e:
            logger.error(f"Failed to log failed request: {str(e)}")
            await self.db.rollback()