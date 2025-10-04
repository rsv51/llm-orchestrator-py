"""
OpenAI provider implementation.
"""
from typing import Dict, Any, AsyncGenerator, Optional
import json
import httpx

from app.providers.base import BaseProvider, ProviderConfig
from app.api.schemas import ChatCompletionRequest, ChatCompletionResponse, ChatCompletionChoice, ChatMessage, Usage, MessageRole
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
        request: ChatCompletionRequest
    ) -> ChatCompletionResponse:
        """
        Send chat completion request to OpenAI.
        
        Args:
            request: Chat completion request
            
        Returns:
            Chat completion response
        """
        # Resolve model name using aliases
        resolved_model = self.config.resolve_model(request.model)
        
        # Prepare request payload with only valid fields
        payload = {
            "model": resolved_model,
            "messages": [msg.model_dump(exclude_none=True) for msg in request.messages],
            "stream": False
        }
        
        # Helper function to add non-None and non-empty values
        def add_if_valid(key: str, value):
            """Add field to payload only if it's not None and not an empty dict/list."""
            if value is not None:
                # Skip empty dicts and lists
                if isinstance(value, (dict, list)) and not value:
                    return
                payload[key] = value
        
        # Add optional parameters with validation
        add_if_valid("temperature", request.temperature)
        add_if_valid("top_p", request.top_p)
        add_if_valid("max_tokens", request.max_tokens)
        add_if_valid("presence_penalty", request.presence_penalty)
        add_if_valid("frequency_penalty", request.frequency_penalty)
        add_if_valid("stop", request.stop)
        add_if_valid("user", request.user)
        
        # Handle tools (dump to dict and exclude None)
        if request.tools:
            payload["tools"] = [tool.model_dump(exclude_none=True) for tool in request.tools]
        
        add_if_valid("tool_choice", request.tool_choice)
        add_if_valid("response_format", request.response_format)
        add_if_valid("seed", request.seed)
        
        # Apply parameter overrides
        payload = self.apply_parameter_overrides(payload)
        
        client = await self.get_client()
        url = f"{self.base_url}/chat/completions"
        headers = self.prepare_headers()
        
        logger.info(
            "Sending OpenAI chat completion request",
            extra={"model": resolved_model, "has_tools": request.tools is not None}
        )
        
        return await self._non_stream_response(client, url, headers, payload, request.model)
    
    async def chat_completion_stream(
        self,
        request: ChatCompletionRequest
    ) -> AsyncGenerator[str, None]:
        """
        Send streaming chat completion request to OpenAI.
        
        Args:
            request: Chat completion request
            
        Yields:
            Server-sent event chunks
        """
        # Resolve model name
        resolved_model = self.config.resolve_model(request.model)
        
        # Prepare payload with only valid fields
        payload = {
            "model": resolved_model,
            "messages": [msg.model_dump(exclude_none=True) for msg in request.messages],
            "stream": True
        }
        
        # Helper function to add non-None and non-empty values
        def add_if_valid(key: str, value):
            """Add field to payload only if it's not None and not an empty dict/list."""
            if value is not None:
                # Skip empty dicts and lists
                if isinstance(value, (dict, list)) and not value:
                    return
                payload[key] = value
        
        # Add all optional parameters with validation
        add_if_valid("temperature", request.temperature)
        add_if_valid("top_p", request.top_p)
        add_if_valid("max_tokens", request.max_tokens)
        add_if_valid("presence_penalty", request.presence_penalty)
        add_if_valid("frequency_penalty", request.frequency_penalty)
        add_if_valid("stop", request.stop)
        add_if_valid("user", request.user)
        
        # Handle tools (dump to dict and exclude None)
        if request.tools:
            payload["tools"] = [tool.model_dump(exclude_none=True) for tool in request.tools]
        
        add_if_valid("tool_choice", request.tool_choice)
        add_if_valid("response_format", request.response_format)
        add_if_valid("seed", request.seed)
        
        payload = self.apply_parameter_overrides(payload)
        
        client = await self.get_client()
        url = f"{self.base_url}/chat/completions"
        headers = self.prepare_headers()
        
        async for chunk in self._stream_response(client, url, headers, payload):
            yield chunk
    
    async def _non_stream_response(
        self,
        client: httpx.AsyncClient,
        url: str,
        headers: Dict[str, str],
        payload: Dict[str, Any],
        original_model: str
    ) -> ChatCompletionResponse:
        """Handle non-streaming response."""
        try:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
            
            # Convert to ChatCompletionResponse
            return ChatCompletionResponse(
                id=data.get("id", "unknown"),
                object=data.get("object", "chat.completion"),
                created=data.get("created", 0),
                model=original_model,
                choices=[
                    ChatCompletionChoice(
                        index=choice.get("index", 0),
                        message=ChatMessage(
                            role=MessageRole(choice["message"]["role"]),
                            content=choice["message"].get("content"),
                            tool_calls=choice["message"].get("tool_calls"),
                            function_call=choice["message"].get("function_call")
                        ),
                        finish_reason=choice.get("finish_reason")
                    )
                    for choice in data.get("choices", [])
                ],
                usage=Usage(
                    prompt_tokens=data.get("usage", {}).get("prompt_tokens", 0),
                    completion_tokens=data.get("usage", {}).get("completion_tokens", 0),
                    total_tokens=data.get("usage", {}).get("total_tokens", 0)
                ) if data.get("usage") else None
            )
        except httpx.HTTPStatusError as e:
            logger.error(
                "OpenAI API error",
                extra={"status_code": e.response.status_code, "error": e.response.text}
            )
            raise
        except Exception as e:
            logger.error("OpenAI request failed", extra={"error": str(e)})
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
                            yield "data: [DONE]\n\n"
                            break
                        if data:  # Only yield non-empty data
                            yield f"data: {data}\n\n"
        except httpx.HTTPStatusError as e:
            logger.error(
                "OpenAI streaming error",
                extra={"status_code": e.response.status_code}
            )
            raise
        except Exception as e:
            logger.error("OpenAI streaming failed", extra={"error": str(e)})
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