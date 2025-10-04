"""
Request router for handling LLM API requests with failover.
"""
import time
import asyncio
from typing import Optional, AsyncGenerator
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
        client_ip: Optional[str] = None
    ) -> ChatCompletionResponse:
        """
        Route request to provider with failover support.
        
        Args:
            provider_name: Target provider name
            request: Chat completion request
            request_id: Unique request ID
            api_key: User API key
            client_ip: Client IP address
            
        Returns:
            Chat completion response
            
        Raises:
            Exception: If all providers fail
        """
        start_time = time.time()
        last_error = None
        retry_count = request.retry_count or settings.max_retry_count
        
        # Get provider from database
        provider = await self._get_provider(provider_name)
        if not provider:
            raise Exception(f"Provider {provider_name} not found")
        
        # Try main provider with retries
        for attempt in range(retry_count + 1):
            try:
                logger.info(
                    f"Routing request to {provider_name} (attempt {attempt + 1}/{retry_count + 1})",
                    extra={"request_id": request_id, "provider": provider_name}
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
                
                # Add provider info to response
                response.provider = provider_name
                
                return response
            
            except Exception as e:
                last_error = e
                logger.warning(
                    f"Request failed on {provider_name}: {str(e)}",
                    extra={
                        "request_id": request_id,
                        "provider": provider_name,
                        "attempt": attempt + 1,
                        "error": str(e)
                    }
                )
                
                # Wait before retry (exponential backoff)
                if attempt < retry_count:
                    wait_time = min(2 ** attempt, 10)  # Max 10 seconds
                    await asyncio.sleep(wait_time)
        
        # All attempts failed
        latency_ms = int((time.time() - start_time) * 1000)
        await self._log_failed_request(
            provider_id=provider.id,
            request=request,
            error=str(last_error),
            latency_ms=latency_ms,
            api_key=api_key,
            client_ip=client_ip
        )
        
        raise Exception(f"All retry attempts failed: {str(last_error)}")
    
    async def route_streaming_request(
        self,
        provider_name: str,
        request: ChatCompletionRequest,
        request_id: str,
        api_key: Optional[str] = None,
        client_ip: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """
        Route streaming request to provider.
        
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
        
        try:
            # Create provider instance
            provider_instance = self.provider_factory.create_provider(
                provider_type=provider.type,
                api_key=provider.api_key,
                base_url=provider.base_url,
                timeout=request.timeout or provider.timeout
            )
            
            # Stream response
            async for chunk in provider_instance.chat_completion_stream(request):
                yield chunk
            
            # Log successful streaming request
            latency_ms = int((time.time() - start_time) * 1000)
            await self._log_request(
                provider_id=provider.id,
                request=request,
                response=None,  # No response object for streaming
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