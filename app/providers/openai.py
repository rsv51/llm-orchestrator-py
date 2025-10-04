"""
OpenAI provider implementation.
"""
from typing import Dict, Any, AsyncGenerator, Optional
import json
import httpx

from app.providers.base import BaseProvider, ProviderConfig
from app.core.logger import get_logger

logger = get_logger(__name__)


class OpenAIProvider(BaseProvider):
    """OpenAI API provider implementation."""
    
    @property
    def provider_type(self) -> str:
        return "openai"
    
    @property
    def default_base_url(self) -> str:
        return "https://api.openai.com/v1"
    
    def prepare_headers(self) -> Dict[str, str]:
        """Prepare OpenAI-specific headers."""
        headers = super().prepare_headers()
        headers["Authorization"] = f"Bearer {self.config.api_key}"
        return headers
    
    async def chat_completion(
        self,
        messages: list[Dict[str, Any]],
        model: str,
        stream: bool = False,
        **kwargs
    ) -> Dict[str, Any] | AsyncGenerator[str, None]:
        """
        Send chat completion request to OpenAI.
        
        Args:
            messages: Chat messages
            model: Model name
            stream: Whether to stream response
            **kwargs: Additional parameters (temperature, max_tokens, etc.)
            
        Returns:
            Response dict or async generator for streaming
        """
        # Resolve model name using aliases
        resolved_model = self.config.resolve_model(model)
        
        # Prepare request payload
        payload = {
            "model": resolved_model,
            "messages": messages,
            "stream": stream,
            **kwargs
        }
        
        # Apply parameter overrides
        payload = self.apply_parameter_overrides(payload)
        
        client = await self.get_client()
        url = f"{self.base_url}/chat/completions"
        headers = self.prepare_headers()
        
        logger.info(
            "Sending OpenAI chat completion request",
            model=resolved_model,
            stream=stream
        )
        
        if stream:
            return self._stream_response(client, url, headers, payload)
        else:
            return await self._non_stream_response(client, url, headers, payload)
    
    async def _non_stream_response(
        self,
        client: httpx.AsyncClient,
        url: str,
        headers: Dict[str, str],
        payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle non-streaming response."""
        try:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(
                "OpenAI API error",
                status_code=e.response.status_code,
                error=e.response.text
            )
            raise
        except Exception as e:
            logger.error("OpenAI request failed", error=str(e))
            raise
    
    async def _stream_response(
        self,
        client: httpx.AsyncClient,
        url: str,
        headers: Dict[str, str],
        payload: Dict[str, Any]
    ) -> AsyncGenerator[str, None]:
        """Handle streaming response with robust SSE parsing."""
        try:
            async with client.stream("POST", url, json=payload, headers=headers) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    # Skip empty lines and comments
                    if not line or line.startswith(":"):
                        continue
                    
                    # Process SSE data lines
                    if line.startswith("data: "):
                        data = line[6:].strip()  # Remove "data: " prefix
                        if data == "[DONE]":
                            break
                        if data:  # Only yield non-empty data
                            yield data
        except httpx.HTTPStatusError as e:
            logger.error(
                "OpenAI streaming error",
                status_code=e.response.status_code
            )
            raise
        except Exception as e:
            logger.error("OpenAI streaming failed", error=str(e))
            raise
    
    async def get_models(self) -> list[str]:
        """
        Get available models from OpenAI.
        
        Returns:
            List of model IDs
        """
        client = await self.get_client()
        url = f"{self.base_url}/models"
        headers = self.prepare_headers()
        
        try:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
            return [model["id"] for model in data.get("data", [])]
        except Exception as e:
            logger.error("Failed to fetch OpenAI models", error=str(e))
            return []
    
    async def validate_credentials(self) -> bool:
        """
        Validate OpenAI API credentials.
        
        Returns:
            True if credentials are valid
        """
        try:
            models = await self.get_models()
            return len(models) > 0
        except Exception as e:
            logger.warning("OpenAI credentials validation failed", error=str(e))
            return False