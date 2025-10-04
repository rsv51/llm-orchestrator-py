"""
Anthropic Claude provider implementation.
"""
from typing import AsyncGenerator, Dict, Any, Optional
import httpx

from app.providers.base import BaseProvider, ProviderConfig
from app.api.schemas import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatCompletionChoice,
    ChatMessage,
    Usage,
    MessageRole
)
from app.core.logger import get_logger

logger = get_logger(__name__)


class AnthropicProvider(BaseProvider):
    """
    Anthropic Claude API provider implementation.
    
    Supports Claude 3 (Opus, Sonnet, Haiku) and Claude 2 models.
    """
    
    def __init__(self, config: ProviderConfig):
        """
        Initialize Anthropic provider.
        
        Args:
            config: Provider configuration
        """
        super().__init__(config)
        self.api_version = "2023-06-01"
    
    @property
    def provider_type(self) -> str:
        return "anthropic"
    
    @property
    def default_base_url(self) -> str:
        return "https://api.anthropic.com"
    
    async def chat_completion(
        self,
        request: ChatCompletionRequest
    ) -> ChatCompletionResponse:
        """
        Send chat completion request to Anthropic API.
        
        Args:
            request: Chat completion request
            
        Returns:
            Chat completion response
        """
        # Convert OpenAI format to Anthropic format
        anthropic_request = self._convert_to_anthropic_format(request)
        
        # Send request
        url = f"{self.base_url}/v1/messages"
        headers = {
            "x-api-key": self.config.api_key,
            "anthropic-version": self.api_version,
            "content-type": "application/json"
        }
        
        client = await self.get_client()
        response = await client.post(
            url,
            json=anthropic_request,
            headers=headers
        )
        response.raise_for_status()
        data = response.json()
        
        # Convert Anthropic response to OpenAI format
        return self._convert_from_anthropic_format(data, request.model)
    
    async def chat_completion_stream(
        self,
        request: ChatCompletionRequest
    ) -> AsyncGenerator[str, None]:
        """
        Send streaming chat completion request to Anthropic API.
        
        Args:
            request: Chat completion request
            
        Yields:
            Server-sent event chunks
        """
        # Convert to Anthropic format
        anthropic_request = self._convert_to_anthropic_format(request)
        anthropic_request["stream"] = True
        
        # Send streaming request
        url = f"{self.base_url}/v1/messages"
        headers = {
            "x-api-key": self.config.api_key,
            "anthropic-version": self.api_version,
            "content-type": "application/json"
        }
        
        client = await self.get_client()
        async with client.stream(
            "POST",
            url,
            json=anthropic_request,
            headers=headers
        ) as response:
            response.raise_for_status()
            
            async for line in response.aiter_lines():
                if not line or not line.startswith("data: "):
                    continue
                
                # Remove "data: " prefix
                data_str = line[6:]
                
                if data_str == "[DONE]":
                    yield "data: [DONE]\n\n"
                    break
                
                # Convert Anthropic event to OpenAI format
                try:
                    import json
                    event_data = json.loads(data_str)
                    openai_chunk = self._convert_stream_chunk(event_data, request.model)
                    
                    if openai_chunk:
                        yield f"data: {json.dumps(openai_chunk)}\n\n"
                except Exception as e:
                    logger.warning(f"Failed to parse stream chunk: {e}")
                    continue
    
    def _convert_to_anthropic_format(
        self,
        request: ChatCompletionRequest
    ) -> Dict[str, Any]:
        """
        Convert OpenAI format request to Anthropic format.
        
        Args:
            request: OpenAI format request
            
        Returns:
            Anthropic format request
        """
        # Extract system message if present
        system_message = None
        messages = []
        
        for msg in request.messages:
            if msg.role == MessageRole.SYSTEM:
                system_message = msg.content
            else:
                messages.append({
                    "role": "user" if msg.role == MessageRole.USER else "assistant",
                    "content": msg.content
                })
        
        # Build Anthropic request
        anthropic_request = {
            "model": self._map_model_name(request.model),
            "messages": messages,
            "max_tokens": request.max_tokens or 4096,
        }
        
        # Add optional parameters
        if system_message:
            anthropic_request["system"] = system_message
        
        if request.temperature is not None:
            anthropic_request["temperature"] = request.temperature
        
        if request.top_p is not None:
            anthropic_request["top_p"] = request.top_p
        
        if request.stop:
            anthropic_request["stop_sequences"] = (
                [request.stop] if isinstance(request.stop, str) else request.stop
            )
        
        return anthropic_request
    
    def _convert_from_anthropic_format(
        self,
        response: Dict[str, Any],
        model: str
    ) -> ChatCompletionResponse:
        """
        Convert Anthropic format response to OpenAI format.
        
        Args:
            response: Anthropic format response
            model: Model name
            
        Returns:
            OpenAI format response
        """
        # Extract content
        content = ""
        if response.get("content"):
            for block in response["content"]:
                if block.get("type") == "text":
                    content += block.get("text", "")
        
        # Map finish reason
        finish_reason_map = {
            "end_turn": "stop",
            "max_tokens": "length",
            "stop_sequence": "stop"
        }
        finish_reason = finish_reason_map.get(
            response.get("stop_reason", ""),
            "stop"
        )
        
        # Build OpenAI response
        return ChatCompletionResponse(
            id=response.get("id", "unknown"),
            object="chat.completion",
            created=int(response.get("created", 0)),
            model=model,
            choices=[
                ChatCompletionChoice(
                    index=0,
                    message=ChatMessage(
                        role=MessageRole.ASSISTANT,
                        content=content
                    ),
                    finish_reason=finish_reason
                )
            ],
            usage=Usage(
                prompt_tokens=response.get("usage", {}).get("input_tokens", 0),
                completion_tokens=response.get("usage", {}).get("output_tokens", 0),
                total_tokens=(
                    response.get("usage", {}).get("input_tokens", 0) +
                    response.get("usage", {}).get("output_tokens", 0)
                )
            )
        )
    
    def _convert_stream_chunk(
        self,
        event: Dict[str, Any],
        model: str
    ) -> Optional[Dict[str, Any]]:
        """
        Convert Anthropic stream event to OpenAI format chunk.
        
        Args:
            event: Anthropic event data
            model: Model name
            
        Returns:
            OpenAI format chunk or None
        """
        event_type = event.get("type")
        
        if event_type == "content_block_delta":
            delta = event.get("delta", {})
            if delta.get("type") == "text_delta":
                return {
                    "id": event.get("message_id", "unknown"),
                    "object": "chat.completion.chunk",
                    "created": 0,
                    "model": model,
                    "choices": [{
                        "index": 0,
                        "delta": {
                            "content": delta.get("text", "")
                        },
                        "finish_reason": None
                    }]
                }
        
        elif event_type == "message_stop":
            return {
                "id": event.get("message_id", "unknown"),
                "object": "chat.completion.chunk",
                "created": 0,
                "model": model,
                "choices": [{
                    "index": 0,
                    "delta": {},
                    "finish_reason": "stop"
                }]
            }
        
        return None
    
    def _map_model_name(self, model: str) -> str:
        """
        Map OpenAI-style model name to Anthropic model name.
        
        Args:
            model: Model name
            
        Returns:
            Anthropic model name
        """
        # Model mapping
        model_map = {
            "claude-3-opus": "claude-3-opus-20240229",
            "claude-3-sonnet": "claude-3-sonnet-20240229",
            "claude-3-haiku": "claude-3-haiku-20240307",
            "claude-3.5-sonnet": "claude-3-5-sonnet-20240620",
            "claude-2": "claude-2.1",
            "claude-2.1": "claude-2.1",
            "claude-2.0": "claude-2.0"
        }
        
        # Return mapped name or original
        return model_map.get(model, model)
    
    async def get_models(self) -> list[str]:
        """
        Get available models from Anthropic.
        
        Returns:
            List of model IDs
        """
        # Anthropic doesn't have a models list endpoint, return static list
        return [
            "claude-3-opus-20240229",
            "claude-3-sonnet-20240229",
            "claude-3-haiku-20240307",
            "claude-3-5-sonnet-20240620",
            "claude-2.1",
            "claude-2.0"
        ]
    
    async def validate_credentials(self) -> bool:
        """
        Validate Anthropic API credentials.
        
        Returns:
            True if credentials are valid
        """
        try:
            test_request = ChatCompletionRequest(
                model="claude-3-haiku",
                messages=[
                    ChatMessage(role=MessageRole.USER, content="Hi")
                ],
                max_tokens=5
            )
            
            await self.chat_completion(test_request)
            return True
        
        except Exception as e:
            logger.error(f"API key validation failed: {e}")
            return False