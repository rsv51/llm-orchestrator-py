"""
API request/response schemas using Pydantic models.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from enum import Enum

from pydantic import BaseModel, Field, field_validator


# ============================================================================
# Enums
# ============================================================================

class MessageRole(str, Enum):
    """Chat message role."""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    FUNCTION = "function"
    TOOL = "tool"


class FinishReason(str, Enum):
    """Completion finish reason."""
    STOP = "stop"
    LENGTH = "length"
    CONTENT_FILTER = "content_filter"
    TOOL_CALLS = "tool_calls"
    FUNCTION_CALL = "function_call"


# ============================================================================
# Chat Completion Schemas (OpenAI compatible)
# ============================================================================

class ChatMessage(BaseModel):
    """Chat message model."""
    role: MessageRole
    content: Optional[str] = None
    name: Optional[str] = None
    function_call: Optional[Dict[str, Any]] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_call_id: Optional[str] = None


class FunctionDefinition(BaseModel):
    """Function definition for function calling."""
    name: str
    description: Optional[str] = None
    parameters: Dict[str, Any]


class ToolDefinition(BaseModel):
    """Tool definition for tool calling."""
    type: str = "function"
    function: FunctionDefinition


class ChatCompletionRequest(BaseModel):
    """Chat completion request model (OpenAI compatible)."""
    model: str
    messages: List[ChatMessage]
    temperature: Optional[float] = Field(default=1.0, ge=0, le=2)
    top_p: Optional[float] = Field(default=1.0, ge=0, le=1)
    n: Optional[int] = Field(default=1, ge=1, le=10)
    stream: Optional[bool] = False
    stop: Optional[Union[str, List[str]]] = None
    max_tokens: Optional[int] = Field(default=None, ge=1)
    presence_penalty: Optional[float] = Field(default=0, ge=-2, le=2)
    frequency_penalty: Optional[float] = Field(default=0, ge=-2, le=2)
    logit_bias: Optional[Dict[str, float]] = None
    user: Optional[str] = None
    functions: Optional[List[FunctionDefinition]] = None
    function_call: Optional[Union[str, Dict[str, str]]] = None
    tools: Optional[List[ToolDefinition]] = None
    tool_choice: Optional[Union[str, Dict[str, Any]]] = None
    response_format: Optional[Dict[str, str]] = None
    seed: Optional[int] = None
    
    # Custom fields for orchestration
    provider: Optional[str] = Field(
        default=None,
        description="Specific provider to use (overrides auto-routing)"
    )
    fallback_providers: Optional[List[str]] = Field(
        default=None,
        description="Ordered list of fallback providers"
    )
    timeout: Optional[int] = Field(
        default=None,
        ge=1,
        description="Request timeout in seconds"
    )
    retry_count: Optional[int] = Field(
        default=3,
        ge=0,
        le=5,
        description="Number of retry attempts"
    )
    
    @field_validator('temperature')
    @classmethod
    def validate_temperature(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and (v < 0 or v > 2):
            raise ValueError('temperature must be between 0 and 2')
        return v


class ChatCompletionChoice(BaseModel):
    """Chat completion choice."""
    index: int
    message: ChatMessage
    finish_reason: Optional[FinishReason] = None
    logprobs: Optional[Dict[str, Any]] = None


class Usage(BaseModel):
    """Token usage information."""
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class ChatCompletionResponse(BaseModel):
    """Chat completion response model (OpenAI compatible)."""
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[ChatCompletionChoice]
    usage: Optional[Usage] = None
    system_fingerprint: Optional[str] = None
    
    # Custom fields
    provider: Optional[str] = Field(
        default=None,
        description="Provider that handled the request"
    )
    latency_ms: Optional[int] = Field(
        default=None,
        description="Request latency in milliseconds"
    )


class ChatCompletionChunk(BaseModel):
    """Streaming chat completion chunk."""
    id: str
    object: str = "chat.completion.chunk"
    created: int
    model: str
    choices: List[Dict[str, Any]]
    system_fingerprint: Optional[str] = None


# ============================================================================
# Models Endpoint Schemas
# ============================================================================

class Model(BaseModel):
    """Model information."""
    id: str
    object: str = "model"
    created: Optional[int] = None
    owned_by: Optional[str] = None
    permission: Optional[List[Dict[str, Any]]] = None
    root: Optional[str] = None
    parent: Optional[str] = None


class ModelsListResponse(BaseModel):
    """Models list response."""
    object: str = "list"
    data: List[Model]


# ============================================================================
# Provider Management Schemas
# ============================================================================

class ProviderBase(BaseModel):
    """Provider base schema."""
    name: str
    type: str
    base_url: Optional[str] = None
    enabled: bool = True
    priority: int = Field(default=100, ge=0, le=1000)
    weight: int = Field(default=100, ge=0, le=1000)
    max_retries: int = Field(default=3, ge=0, le=10)
    timeout: int = Field(default=60, ge=1, le=300)
    rate_limit: Optional[int] = Field(default=None, ge=1)


class ProviderCreate(ProviderBase):
    """Provider creation schema."""
    api_key: str = Field(min_length=1, description="API key for the provider")


class ProviderUpdate(BaseModel):
    """Provider update schema."""
    name: Optional[str] = None
    type: Optional[str] = None
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    enabled: Optional[bool] = None
    priority: Optional[int] = Field(default=None, ge=0, le=1000)
    weight: Optional[int] = Field(default=None, ge=0, le=1000)
    max_retries: Optional[int] = Field(default=None, ge=0, le=10)
    timeout: Optional[int] = Field(default=None, ge=1, le=300)
    rate_limit: Optional[int] = Field(default=None, ge=1)


class ProviderResponse(BaseModel):
    """Provider response schema - matches database model exactly."""
    model_config = {"from_attributes": True}
    
    id: int
    name: str
    type: str
    api_key: str
    base_url: Optional[str] = None
    enabled: bool
    priority: int
    weight: int
    max_retries: int
    timeout: int
    rate_limit: Optional[int] = None
    created_at: datetime
    updated_at: datetime


# ============================================================================
# Health Check Schemas
# ============================================================================

class ProviderHealthStatus(BaseModel):
    """Provider health status."""
    provider_id: int
    provider_name: str
    is_healthy: bool
    response_time_ms: Optional[float] = None
    error_message: Optional[str] = None
    last_check: datetime
    consecutive_failures: int
    success_rate: float


class SystemHealthResponse(BaseModel):
    """System health response."""
    status: str  # "healthy", "degraded", "unhealthy"
    timestamp: datetime
    providers: List[ProviderHealthStatus]
    database_status: str
    cache_status: str


# ============================================================================
# Statistics Schemas
# ============================================================================

class ProviderStats(BaseModel):
    """Provider statistics."""
    provider_id: int
    provider_name: str
    total_requests: int
    successful_requests: int
    failed_requests: int
    success_rate: float
    avg_response_time_ms: float
    total_tokens: int
    total_cost: float


class SystemStats(BaseModel):
    """System statistics."""
    total_requests: int
    successful_requests: int
    failed_requests: int
    success_rate: float
    avg_response_time_ms: float
    providers: List[ProviderStats]
    timestamp: datetime


# ============================================================================
# Error Response Schemas
# ============================================================================

class ErrorDetail(BaseModel):
    """Error detail."""
    code: str
    message: str
    details: Optional[Dict[str, Any]] = None


class ErrorResponse(BaseModel):
    """Error response."""
    error: ErrorDetail
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    request_id: Optional[str] = None


# ============================================================================
# Model Configuration Schemas (Simplified like llmio-master)
# ============================================================================

class ModelConfigBase(BaseModel):
    """Model configuration base schema - simplified."""
    name: str
    remark: Optional[str] = None
    max_retry: int = Field(default=3, ge=0, le=10)
    timeout: int = Field(default=30, ge=1, le=300)
    enabled: bool = True


class ModelConfigCreate(ModelConfigBase):
    """Model configuration creation schema."""
    pass


class ModelConfigUpdate(BaseModel):
    """Model configuration update schema."""
    name: Optional[str] = None
    remark: Optional[str] = None
    max_retry: Optional[int] = Field(default=None, ge=0, le=10)
    timeout: Optional[int] = Field(default=None, ge=1, le=300)
    enabled: Optional[bool] = None


class ModelConfigResponse(ModelConfigBase):
    """Model configuration response schema."""
    model_config = {"from_attributes": True}
    
    id: int
    created_at: datetime
    updated_at: datetime


# ============================================================================
# Model-Provider Association Schemas (like llmio-master)
# ============================================================================

class ModelProviderBase(BaseModel):
    """Model-Provider association base schema."""
    model_config = {"protected_namespaces": ()}
    
    model_id: int = Field(gt=0)
    provider_id: int = Field(gt=0)
    provider_model: str = Field(min_length=1)
    weight: int = Field(default=1, ge=1, le=1000)
    tool_call: bool = True
    structured_output: bool = True
    image: bool = False
    enabled: bool = True


class ModelProviderCreate(ModelProviderBase):
    """Model-Provider association creation schema."""
    pass


class ModelProviderUpdate(BaseModel):
    """Model-Provider association update schema."""
    provider_model: Optional[str] = None
    weight: Optional[int] = Field(default=None, ge=1, le=1000)
    tool_call: Optional[bool] = None
    structured_output: Optional[bool] = None
    image: Optional[bool] = None
    enabled: Optional[bool] = None


class ModelProviderResponse(ModelProviderBase):
    """Model-Provider association response schema."""
    model_config = {"from_attributes": True}
    
    id: int
    created_at: datetime
    updated_at: datetime


class ModelProviderWithDetails(ModelProviderResponse):
    """Model-Provider association with provider details."""
    model_config = {"protected_namespaces": (), "from_attributes": True}
    
    provider_name: Optional[str] = None
    provider_type: Optional[str] = None
    model_name: Optional[str] = None


# ============================================================================
# Request Log Schemas
# ============================================================================

class RequestLogResponse(BaseModel):
    """Request log response schema."""
    model_config = {"from_attributes": True}
    
    id: int
    provider_id: int
    provider_name: str
    model: str
    endpoint: str
    method: str
    status_code: Optional[int] = None
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    cost: Optional[float] = None
    latency_ms: Optional[int] = None
    error_message: Optional[str] = None
    user_id: Optional[str] = None
    ip_address: Optional[str] = None
    created_at: datetime


class RequestLogListResponse(BaseModel):
    """Request log list response."""
    total: int
    page: int
    page_size: int
    logs: List[RequestLogResponse]