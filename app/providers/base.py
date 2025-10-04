"""
Base provider abstract class and configuration.
"""
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, AsyncGenerator
from dataclasses import dataclass
import httpx

from app.core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ProviderConfig:
    """Provider configuration."""
    
    api_key: str
    base_url: Optional[str] = None
    timeout: int = 30
    max_retries: int = 3
    model_aliases: Optional[Dict[str, str]] = None
    parameter_overrides: Optional[Dict[str, Any]] = None
    
    def get_effective_base_url(self, default_url: str) -> str:
        """Get effective base URL (use config or default)."""
        return self.base_url or default_url
    
    def resolve_model(self, model: str) -> str:
        """Resolve model name using aliases."""
        if self.model_aliases and model in self.model_aliases:
            return self.model_aliases[model]
        return model


class BaseProvider(ABC):
    """Abstract base class for LLM providers."""
    
    def __init__(self, config: ProviderConfig):
        """
        Initialize provider.
        
        Args:
            config: Provider configuration
        """
        self.config = config
        self._client: Optional[httpx.AsyncClient] = None
    
    @property
    @abstractmethod
    def provider_type(self) -> str:
        """Provider type identifier (e.g., 'openai', 'anthropic')."""
        pass
    
    @property
    @abstractmethod
    def default_base_url(self) -> str:
        """Default base URL for the provider."""
        pass
    
    @property
    def base_url(self) -> str:
        """Get effective base URL."""
        return self.config.get_effective_base_url(self.default_base_url)
    
    async def get_client(self) -> httpx.AsyncClient:
        """
        Get or create HTTP client with connection pooling.
        
        Returns:
            Async HTTP client
        """
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.config.timeout),
                limits=httpx.Limits(
                    max_keepalive_connections=10,
                    max_connections=20,
                    keepalive_expiry=30.0
                )
            )
        return self._client
    
    async def close(self) -> None:
        """Close HTTP client and cleanup resources."""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    @abstractmethod
    async def chat_completion(
        self,
        request: 'ChatCompletionRequest'
    ) -> 'ChatCompletionResponse':
        """
        Send chat completion request.
        
        Args:
            request: Chat completion request object
            
        Returns:
            Chat completion response
        """
        pass
    
    @abstractmethod
    async def chat_completion_stream(
        self,
        request: 'ChatCompletionRequest'
    ) -> AsyncGenerator[str, None]:
        """
        Send streaming chat completion request.
        
        Args:
            request: Chat completion request object
            
        Yields:
            Server-sent event chunks
        """
        pass
    
    @abstractmethod
    async def get_models(self) -> list[str]:
        """
        Get available models from provider.
        
        Returns:
            List of model names
        """
        pass
    
    @abstractmethod
    async def validate_credentials(self) -> bool:
        """
        Validate API credentials.
        
        Returns:
            True if credentials are valid
        """
        pass
    
    def prepare_headers(self) -> Dict[str, str]:
        """
        Prepare common request headers.
        
        Returns:
            Headers dictionary
        """
        return {
            "Content-Type": "application/json",
            "User-Agent": "llm-orchestrator/1.0"
        }
    
    def apply_parameter_overrides(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply parameter overrides from configuration.
        
        Args:
            params: Original parameters
            
        Returns:
            Parameters with overrides applied
        """
        if not self.config.parameter_overrides:
            return params
        
        result = params.copy()
        for key, value in self.config.parameter_overrides.items():
            result[key] = value
        
        return result
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.get_client()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()