"""
Google Gemini provider implementation.
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


class GeminiProvider(BaseProvider):
    """
    Google Gemini API provider implementation.
    
    Supports Gemini Pro, Gemini Pro Vision, and other Gemini models.
    """
    
    def __init__(self, config: ProviderConfig):
        """
        Initialize Gemini provider.
        
        Args:
            config: Provider configuration
        """
        super().__init__(config)
        self.api_version = "v1beta"
    
    @property
    def provider_type(self) -> str:
        return "gemini"
    
    @property
    def default_base_url(self) -> str:
        return "https://generativelanguage.googleapis.com"
    
    async def chat_completion(
        self,
        request: ChatCompletionRequest
    ) -> ChatCompletionResponse:
        """
        Send chat completion request to Gemini API.
        
        Args:
            request: Chat completion request
            
        Returns:
            Chat completion response
        """
        # Convert OpenAI format to Gemini format
        gemini_request = self._convert_to_gemini_format(request)
        
        # Build URL
        model_name = self._map_model_name(request.model)
        url = f"{self.base_url}/{self.api_version}/models/{model_name}:generateContent"
        
        # Add API key as query parameter
        params = {"key": self.config.api_key}
        
        # Send request
        client = await self.get_client()
        response = await client.post(
            url,
            json=gemini_request,
            params=params
        )
        response.raise_for_status()
        data = response.json()
        
        # Convert Gemini response to OpenAI format
        return self._convert_from_gemini_format(data, request.model)
    
    async def chat_completion_stream(
        self,
        request: ChatCompletionRequest
    ) -> AsyncGenerator[str, None]:
        """
        Send streaming chat completion request to Gemini API.
        
        Args:
            request: Chat completion request
            
        Yields:
            Server-sent event chunks
        """
        # Convert to Gemini format
        gemini_request = self._convert_to_gemini_format(request)
        
        # Build URL for streaming
        model_name = self._map_model_name(request.model)
        url = f"{self.base_url}/{self.api_version}/models/{model_name}:streamGenerateContent"
        
        # Add API key
        params = {"key": self.config.api_key, "alt": "sse"}
        
        # Send streaming request
        client = await self.get_client()
        async with client.stream(
            "POST",
            url,
            json=gemini_request,
            params=params
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
                
                # Convert Gemini chunk to OpenAI format
                try:
                    import json
                    chunk_data = json.loads(data_str)
                    openai_chunk = self._convert_stream_chunk(chunk_data, request.model)
                    
                    if openai_chunk:
                        yield f"data: {json.dumps(openai_chunk)}\n\n"
                except Exception as e:
                    logger.warning(f"Failed to parse stream chunk: {e}")
                    continue
    
    def _convert_to_gemini_format(
        self,
        request: ChatCompletionRequest
    ) -> Dict[str, Any]:
        """
        Convert OpenAI format request to Gemini format.
        
        Args:
            request: OpenAI format request
            
        Returns:
            Gemini format request
        """
        # Build Gemini contents array
        contents = []
        system_instruction = None
        
        for msg in request.messages:
            if msg.role == MessageRole.SYSTEM:
                # Gemini uses systemInstruction separately
                system_instruction = msg.content
            else:
                role = "user" if msg.role == MessageRole.USER else "model"
                contents.append({
                    "role": role,
                    "parts": [{"text": msg.content}]
                })
        
        # Build Gemini request
        gemini_request = {
            "contents": contents
        }
        
        # Add system instruction if present
        if system_instruction:
            gemini_request["systemInstruction"] = {
                "parts": [{"text": system_instruction}]
            }
        
        # Add generation config
        generation_config = {}
        
        if request.temperature is not None:
            generation_config["temperature"] = request.temperature
        
        if request.top_p is not None:
            generation_config["topP"] = request.top_p
        
        if request.max_tokens is not None:
            generation_config["maxOutputTokens"] = request.max_tokens
        
        if request.stop:
            stop_sequences = (
                [request.stop] if isinstance(request.stop, str) else request.stop
            )
            generation_config["stopSequences"] = stop_sequences
        
        if generation_config:
            gemini_request["generationConfig"] = generation_config
        
        return gemini_request
    
    def _convert_from_gemini_format(
        self,
        response: Dict[str, Any],
        model: str
    ) -> ChatCompletionResponse:
        """
        Convert Gemini format response to OpenAI format.
        
        Args:
            response: Gemini format response
            model: Model name
            
        Returns:
            OpenAI format response
        """
        # Extract content from first candidate
        content = ""
        finish_reason = "stop"
        
        if response.get("candidates"):
            candidate = response["candidates"][0]
            
            # Extract text from parts
            if candidate.get("content", {}).get("parts"):
                for part in candidate["content"]["parts"]:
                    if "text" in part:
                        content += part["text"]
            
            # Map finish reason
            finish_reason_map = {
                "STOP": "stop",
                "MAX_TOKENS": "length",
                "SAFETY": "content_filter",
                "RECITATION": "content_filter",
                "OTHER": "stop"
            }
            gemini_finish = candidate.get("finishReason", "STOP")
            finish_reason = finish_reason_map.get(gemini_finish, "stop")
        
        # Extract usage metadata
        usage_metadata = response.get("usageMetadata", {})
        prompt_tokens = usage_metadata.get("promptTokenCount", 0)
        completion_tokens = usage_metadata.get("candidatesTokenCount", 0)
        
        # Build OpenAI response
        return ChatCompletionResponse(
            id=f"gemini-{hash(content) % 1000000}",
            object="chat.completion",
            created=0,
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
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens
            )
        )
    
    def _convert_stream_chunk(
        self,
        chunk: Dict[str, Any],
        model: str
    ) -> Optional[Dict[str, Any]]:
        """
        Convert Gemini stream chunk to OpenAI format.
        
        Args:
            chunk: Gemini chunk data
            model: Model name
            
        Returns:
            OpenAI format chunk or None
        """
        if not chunk.get("candidates"):
            return None
        
        candidate = chunk["candidates"][0]
        
        # Extract text from parts
        content = ""
        if candidate.get("content", {}).get("parts"):
            for part in candidate["content"]["parts"]:
                if "text" in part:
                    content += part["text"]
        
        # Check finish reason
        finish_reason = None
        if candidate.get("finishReason"):
            finish_reason_map = {
                "STOP": "stop",
                "MAX_TOKENS": "length",
                "SAFETY": "content_filter",
                "RECITATION": "content_filter"
            }
            finish_reason = finish_reason_map.get(
                candidate["finishReason"],
                "stop"
            )
        
        return {
            "id": f"gemini-chunk-{hash(str(chunk)) % 1000000}",
            "object": "chat.completion.chunk",
            "created": 0,
            "model": model,
            "choices": [{
                "index": 0,
                "delta": {
                    "content": content
                } if content else {},
                "finish_reason": finish_reason
            }]
        }
    
    def _map_model_name(self, model: str) -> str:
        """
        Map OpenAI-style model name to Gemini model name.
        
        Args:
            model: Model name
            
        Returns:
            Gemini model name
        """
        # Model mapping
        model_map = {
            "gemini-pro": "gemini-pro",
            "gemini-pro-vision": "gemini-pro-vision",
            "gemini-1.5-pro": "gemini-1.5-pro-latest",
            "gemini-1.5-flash": "gemini-1.5-flash-latest",
            "gemini-ultra": "gemini-ultra"
        }
        
        # Return mapped name or original
        return model_map.get(model, model)
    
    async def get_models(self) -> list[str]:
        """
        Get available models from Gemini.
        
        Returns:
            List of model IDs
        """
        # Return static list of available Gemini models
        return [
            "gemini-pro",
            "gemini-pro-vision",
            "gemini-1.5-pro-latest",
            "gemini-1.5-flash-latest",
            "gemini-ultra"
        ]
    
    async def validate_credentials(self) -> bool:
        """
        Validate Gemini API credentials.
        
        Returns:
            True if credentials are valid
        """
        try:
            test_request = ChatCompletionRequest(
                model="gemini-pro",
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