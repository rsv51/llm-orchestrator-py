"""
Provider factory for creating provider instances.
"""
from typing import Dict, Type
import json

from app.providers.base import BaseProvider, ProviderConfig
from app.providers.openai import OpenAIProvider
from app.providers.anthropic import AnthropicProvider
from app.providers.gemini import GeminiProvider
from app.core.logger import get_logger

logger = get_logger(__name__)


class ProviderFactory:
    """Factory for creating provider instances."""
    
    # Registry of provider types
    _providers: Dict[str, Type[BaseProvider]] = {
        "openai": OpenAIProvider,
        "anthropic": AnthropicProvider,
        "gemini": GeminiProvider,
    }
    
    @classmethod
    def create_provider(
        cls,
        provider_type: str,
        api_key: str,
        base_url: str = None,
        timeout: int = 60,
        **kwargs
    ) -> BaseProvider:
        """
        Create a provider instance (simplified interface).
        
        Args:
            provider_type: Provider type (openai, anthropic, gemini)
            api_key: API key for the provider
            base_url: Optional base URL
            timeout: Request timeout in seconds
            **kwargs: Additional provider-specific parameters
            
        Returns:
            Provider instance
            
        Raises:
            ValueError: If provider type is not supported
        """
        if provider_type not in cls._providers:
            raise ValueError(
                f"Unsupported provider type: {provider_type}. "
                f"Available types: {', '.join(cls._providers.keys())}"
            )
        
        # Create provider instance with direct parameters
        provider_class = cls._providers[provider_type]
        provider = provider_class(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout
        )
        
        logger.info(
            "Created provider instance",
            provider_type=provider_type,
            base_url=base_url or "default"
        )
        
        return provider
    
    @classmethod
    def create_provider_from_config(
        cls,
        provider_type: str,
        config_json: str
    ) -> BaseProvider:
        """
        Create a provider instance from JSON configuration.
        
        Args:
            provider_type: Provider type (openai, anthropic, gemini)
            config_json: JSON string with provider configuration
            
        Returns:
            Provider instance
            
        Raises:
            ValueError: If provider type is not supported
            json.JSONDecodeError: If config_json is invalid
        """
        if provider_type not in cls._providers:
            raise ValueError(
                f"Unsupported provider type: {provider_type}. "
                f"Available types: {', '.join(cls._providers.keys())}"
            )
        
        # Parse configuration
        config_dict = json.loads(config_json)
        
        # Extract common configuration
        api_key = config_dict.get("api_key")
        if not api_key:
            raise ValueError("api_key is required in provider configuration")
        
        base_url = config_dict.get("base_url")
        timeout = config_dict.get("timeout", 60)
        
        # Create provider instance
        return cls.create_provider(
            provider_type=provider_type,
            api_key=api_key,
            base_url=base_url,
            timeout=timeout
        )
    
    @classmethod
    def register_provider(
        cls,
        provider_type: str,
        provider_class: Type[BaseProvider]
    ) -> None:
        """
        Register a new provider type.
        
        Args:
            provider_type: Provider type identifier
            provider_class: Provider class
        """
        cls._providers[provider_type] = provider_class
        logger.info("Registered provider type", provider_type=provider_type)
    
    @classmethod
    def get_supported_types(cls) -> list[str]:
        """
        Get list of supported provider types.
        
        Returns:
            List of provider type identifiers
        """
        return list(cls._providers.keys())