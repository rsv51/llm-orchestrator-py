"""
Load balancer for distributing requests across providers.
"""
import random
from typing import List, Optional, Dict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import RedisCache
from app.core.logger import get_logger
from app.models.provider import Provider
from app.models.health import ProviderHealth

logger = get_logger(__name__)


class LoadBalancer:
    """
    Load balancer for selecting providers based on weights and health.
    
    Implements weighted random selection algorithm that considers:
    - Provider weights
    - Provider health status
    - Provider priority
    """
    
    def __init__(self, db: AsyncSession, cache: RedisCache):
        """
        Initialize load balancer.
        
        Args:
            db: Database session
            cache: Redis cache instance
        """
        self.db = db
        self.cache = cache
    
    async def select_provider(
        self,
        model: Optional[str] = None,
        fallback_providers: Optional[List[str]] = None
    ) -> str:
        """
        Select a provider using weighted random algorithm.
        
        Args:
            model: Model name (optional, for future model-specific routing)
            fallback_providers: List of fallback provider names to try in order
            
        Returns:
            Selected provider name
            
        Raises:
            Exception: If no healthy providers available
        """
        # Try cache first
        cache_key = f"balancer:providers:{model or 'default'}"
        cached_providers = await self.cache.get(cache_key)
        
        if cached_providers:
            providers_data = cached_providers
            logger.debug("Using cached providers list")
        else:
            # Query healthy providers
            providers_data = await self._get_healthy_providers()
            
            if not providers_data:
                raise Exception("No healthy providers available")
            
            # Cache for 30 seconds
            await self.cache.set(cache_key, providers_data, ttl=30)
        
        # If fallback list provided, try those first
        if fallback_providers:
            for fallback_name in fallback_providers:
                for provider_data in providers_data:
                    if provider_data["name"] == fallback_name and provider_data["is_healthy"]:
                        logger.info(f"Using fallback provider: {fallback_name}")
                        return fallback_name
        
        # Select using weighted random
        selected = self._weighted_random_selection(providers_data)
        
        logger.info(
            f"Load balancer selected provider: {selected}",
            extra={
                "provider": selected,
                "model": model,
                "total_providers": len(providers_data)
            }
        )
        
        return selected
    
    async def get_all_healthy_providers(self, model: Optional[str] = None) -> List[str]:
        """
        Get all healthy provider names for failover.
        
        Args:
            model: Model name (optional, for future model-specific filtering)
            
        Returns:
            List of healthy provider names ordered by priority and weight
        """
        # Try cache first
        cache_key = f"balancer:providers:{model or 'default'}"
        cached_providers = await self.cache.get(cache_key)
        
        if cached_providers:
            providers_data = cached_providers
        else:
            providers_data = await self._get_healthy_providers()
            if providers_data:
                await self.cache.set(cache_key, providers_data, ttl=30)
        
        # Return provider names sorted by priority (desc) then weight (desc)
        sorted_providers = sorted(
            providers_data,
            key=lambda p: (p["priority"], p["weight"]),
            reverse=True
        )
        
        return [p["name"] for p in sorted_providers]
    
    async def _get_healthy_providers(self) -> List[Dict]:
        """
        Get list of healthy providers from database.
        
        Returns:
            List of provider data dictionaries
        """
        query = (
            select(Provider, ProviderHealth)
            .join(ProviderHealth, Provider.id == ProviderHealth.provider_id, isouter=True)
            .where(Provider.enabled == True)
            .order_by(Provider.priority.desc())
        )
        
        result = await self.db.execute(query)
        rows = result.all()
        
        providers_data = []
        for provider, health in rows:
            # Consider provider healthy if:
            # 1. No health record yet (new provider)
            # 2. Health check shows healthy
            is_healthy = health is None or health.is_healthy
            
            if is_healthy:
                providers_data.append({
                    "id": provider.id,
                    "name": provider.name,
                    "weight": provider.weight,
                    "priority": provider.priority,
                    "is_healthy": is_healthy
                })
        
        return providers_data
    
    def _weighted_random_selection(self, providers: List[Dict]) -> str:
        """
        Select provider using weighted random algorithm.
        
        Higher weight = higher probability of selection.
        
        Args:
            providers: List of provider data dictionaries
            
        Returns:
            Selected provider name
        """
        if not providers:
            raise Exception("No providers available for selection")
        
        # If only one provider, return it
        if len(providers) == 1:
            return providers[0]["name"]
        
        # Calculate total weight
        total_weight = sum(p["weight"] for p in providers)
        
        if total_weight == 0:
            # If all weights are 0, use equal probability
            return random.choice(providers)["name"]
        
        # Weighted random selection
        rand = random.uniform(0, total_weight)
        cumulative = 0
        
        for provider in providers:
            cumulative += provider["weight"]
            if rand <= cumulative:
                return provider["name"]
        
        # Fallback (should never reach here)
        return providers[-1]["name"]
    
    async def get_provider_stats(self) -> Dict[str, Dict]:
        """
        Get statistics for all providers.
        
        Returns:
            Dictionary mapping provider names to their stats
        """
        query = (
            select(Provider, ProviderHealth)
            .join(ProviderHealth, Provider.id == ProviderHealth.provider_id, isouter=True)
            .where(Provider.enabled == True)
        )
        
        result = await self.db.execute(query)
        rows = result.all()
        
        stats = {}
        for provider, health in rows:
            stats[provider.name] = {
                "id": provider.id,
                "enabled": provider.enabled,
                "priority": provider.priority,
                "weight": provider.weight,
                "is_healthy": health.is_healthy if health else None,
                "response_time_ms": health.response_time_ms if health else None,
                "success_rate": health.success_rate if health else None,
                "consecutive_failures": health.consecutive_failures if health else 0
            }
        
        return stats