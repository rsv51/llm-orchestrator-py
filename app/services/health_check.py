"""
Health check service for monitoring provider availability.
"""
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.logger import get_logger
from app.models.provider import Provider
from app.models.health import ProviderHealth
from app.providers.factory import ProviderFactory
from app.api.schemas import ChatCompletionRequest, ChatMessage, MessageRole

logger = get_logger(__name__)


class HealthCheckService:
    """
    Service for performing health checks on providers.
    
    Features:
    - Periodic health checks
    - Response time tracking
    - Consecutive failure counting
    - Success rate calculation
    - Automatic provider disabling on sustained failures
    """
    
    def __init__(self):
        """Initialize health check service."""
        self.provider_factory = ProviderFactory()
        self.check_interval = settings.health_check_interval
        self.max_errors = settings.health_check_max_errors
        self.retry_hours = settings.health_check_retry_hours
    
    async def start(self):
        """Start the health check loop."""
        logger.info(f"Starting health check service (interval: {self.check_interval}s)")
        
        while True:
            try:
                await self.check_all_providers()
            except Exception as e:
                logger.error(f"Health check loop error: {str(e)}", exc_info=True)
            
            # Wait before next check
            await asyncio.sleep(self.check_interval)
    
    async def check_all_providers(self):
        """Check health of all enabled providers."""
        async with AsyncSessionLocal() as db:
            try:
                # Get all enabled providers
                query = select(Provider).where(Provider.enabled == True)
                result = await db.execute(query)
                providers = result.scalars().all()
                
                if not providers:
                    logger.debug("No enabled providers to check")
                    return
                
                logger.info(f"Checking health of {len(providers)} providers")
                
                # Check each provider
                tasks = [
                    self.check_provider_health(db, provider)
                    for provider in providers
                ]
                await asyncio.gather(*tasks, return_exceptions=True)
                
                await db.commit()
                
            except Exception as e:
                logger.error(f"Failed to check providers: {str(e)}", exc_info=True)
                await db.rollback()
    
    async def check_provider_health(
        self,
        db: AsyncSession,
        provider: Provider
    ) -> Dict:
        """
        Check health of a single provider.
        
        Args:
            db: Database session
            provider: Provider to check
            
        Returns:
            Health check result dictionary
        """
        logger.debug(f"Checking provider: {provider.name}")
        
        # Get existing health record
        query = select(ProviderHealth).where(
            ProviderHealth.provider_id == provider.id
        )
        result = await db.execute(query)
        health = result.scalar_one_or_none()
        
        # Create if doesn't exist
        if not health:
            health = ProviderHealth(
                provider_id=provider.id,
                is_healthy=True,
                consecutive_failures=0,
                total_checks=0,
                successful_checks=0,
                last_check=datetime.utcnow()
            )
            db.add(health)
        
        # Perform health check
        start_time = datetime.utcnow()
        is_healthy = False
        response_time_ms = None
        error_message = None
        
        try:
            # Create provider instance
            provider_instance = self.provider_factory.create_provider(
                provider_type=provider.type,
                api_key=provider.api_key,
                base_url=provider.base_url,
                timeout=30  # 30 second timeout for health checks
            )
            
            # Create simple test request
            test_request = ChatCompletionRequest(
                model="test",
                messages=[
                    ChatMessage(
                        role=MessageRole.USER,
                        content="Hi"
                    )
                ],
                max_tokens=5,
                temperature=0
            )
            
            # Send request
            response = await provider_instance.chat_completion(test_request)
            
            # Calculate response time
            response_time_ms = int(
                (datetime.utcnow() - start_time).total_seconds() * 1000
            )
            
            is_healthy = True
            logger.info(
                f"Provider {provider.name} is healthy",
                extra={
                    "provider": provider.name,
                    "response_time_ms": response_time_ms
                }
            )
        
        except Exception as e:
            error_message = str(e)
            logger.warning(
                f"Provider {provider.name} health check failed: {error_message}",
                extra={"provider": provider.name, "error": error_message}
            )
        
        # Update health record
        health.total_checks += 1
        health.last_check = datetime.utcnow()
        health.response_time_ms = response_time_ms
        health.error_message = error_message
        
        if is_healthy:
            health.is_healthy = True
            health.successful_checks += 1
            health.consecutive_failures = 0
        else:
            health.consecutive_failures += 1
            
            # Mark as unhealthy if consecutive failures exceed threshold
            if health.consecutive_failures >= self.max_errors:
                health.is_healthy = False
                logger.warning(
                    f"Provider {provider.name} marked as unhealthy "
                    f"({health.consecutive_failures} consecutive failures)"
                )
        
        # Calculate success rate
        if health.total_checks > 0:
            health.success_rate = (
                health.successful_checks / health.total_checks * 100
            )
        
        return {
            "provider_id": provider.id,
            "provider_name": provider.name,
            "is_healthy": health.is_healthy,
            "response_time_ms": response_time_ms,
            "consecutive_failures": health.consecutive_failures
        }
    
    async def manual_check(self, provider_name: str) -> Dict:
        """
        Manually trigger health check for a provider.
        
        Args:
            provider_name: Provider name
            
        Returns:
            Health check result
        """
        async with AsyncSessionLocal() as db:
            try:
                # Get provider
                query = select(Provider).where(
                    Provider.name == provider_name
                )
                result = await db.execute(query)
                provider = result.scalar_one_or_none()
                
                if not provider:
                    raise Exception(f"Provider {provider_name} not found")
                
                # Perform check
                result = await self.check_provider_health(db, provider)
                await db.commit()
                
                return result
            
            except Exception as e:
                await db.rollback()
                raise


# Global health check service instance
health_check_service = HealthCheckService()


async def start_health_check_service():
    """Start the health check service as a background task."""
    if settings.health_check_enabled:
        logger.info("Health check service is enabled")
        await health_check_service.start()
    else:
        logger.info("Health check service is disabled")