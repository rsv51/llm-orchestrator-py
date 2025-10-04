# LLM Orchestrator API 使用指南

本文档详细说明如何使用 LLM Orchestrator API。

## 目录

- [快速开始](#快速开始)
- [认证](#认证)
- [API端点](#api端点)
- [使用示例](#使用示例)
- [错误处理](#错误处理)
- [最佳实践](#最佳实践)

## 快速开始

### 基本请求

```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -d '{
    "model": "gpt-3.5-turbo",
    "messages": [
      {"role": "user", "content": "Hello!"}
    ]
  }'
```

### Python客户端

```python
import openai

# 配置客户端
openai.api_base = "http://localhost:8000/v1"
openai.api_key = "YOUR_API_KEY"

# 发送请求
response = openai.ChatCompletion.create(
    model="gpt-3.5-turbo",
    messages=[
        {"role": "user", "content": "Hello!"}
    ]
)

print(response.choices[0].message.content)
```

## 认证

### API密钥

在请求头中提供API密钥:

```bash
# Bearer Token方式
Authorization: Bearer YOUR_API_KEY

# 或者使用X-API-Key头
X-API-Key: YOUR_API_KEY
```

### 管理员密钥

管理端点需要管理员密钥:

```bash
# 使用管理员密钥
Authorization: Bearer YOUR_ADMIN_KEY

# 或
X-Admin-Key: YOUR_ADMIN_KEY
```

## API端点

### 1. 聊天完成 (Chat Completions)

**端点**: `POST /v1/chat/completions`

OpenAI兼容的聊天完成API。

**请求参数**:

```json
{
  "model": "gpt-3.5-turbo",           // 必需: 模型名称
  "messages": [                        // 必需: 消息列表
    {
      "role": "system|user|assistant",
      "content": "消息内容"
    }
  ],
  "temperature": 1.0,                  // 可选: 0-2
  "top_p": 1.0,                        // 可选: 0-1
  "n": 1,                              // 可选: 生成数量
  "stream": false,                     // 可选: 是否流式
  "max_tokens": null,                  // 可选: 最大token数
  "presence_penalty": 0,               // 可选: -2到2
  "frequency_penalty": 0,              // 可选: -2到2
  
  // 编排特有参数
  "provider": "openai",                // 可选: 指定提供商
  "fallback_providers": ["anthropic"], // 可选: 备用提供商列表
  "timeout": 60,                       // 可选: 超时秒数
  "retry_count": 3                     // 可选: 重试次数
}
```

**响应**:

```json
{
  "id": "chatcmpl-123",
  "object": "chat.completion",
  "created": 1677652288,
  "model": "gpt-3.5-turbo",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "Hello! How can I help you today?"
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 10,
    "completion_tokens": 9,
    "total_tokens": 19
  },
  "provider": "openai",      // 实际处理的提供商
  "latency_ms": 1234         // 请求延迟(毫秒)
}
```

**流式响应**:

```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-3.5-turbo",
    "messages": [{"role": "user", "content": "Hello!"}],
    "stream": true
  }'
```

响应格式(Server-Sent Events):
```
data: {"id":"chatcmpl-123","object":"chat.completion.chunk",...}

data: {"id":"chatcmpl-123","object":"chat.completion.chunk",...}

data: [DONE]
```

### 2. 模型列表 (Models)

**端点**: `GET /v1/models`

获取可用模型列表。

**响应**:

```json
{
  "object": "list",
  "data": [
    {
      "id": "openai:gpt-3.5-turbo",
      "object": "model",
      "created": 1677610602,
      "owned_by": "openai"
    },
    {
      "id": "anthropic:claude-3-sonnet",
      "object": "model",
      "created": 1677610602,
      "owned_by": "anthropic"
    }
  ]
}
```

### 3. 模型详情

**端点**: `GET /v1/models/{model_id}`

获取特定模型信息。

```bash
curl http://localhost:8000/v1/models/openai:gpt-3.5-turbo \
  -H "Authorization: Bearer YOUR_API_KEY"
```

### 4. 系统健康检查

**端点**: `GET /health` 或 `GET /healthz`

检查服务健康状态(无需认证)。

**响应**:

```json
{
  "status": "healthy",
  "service": "llm-orchestrator"
}
```

### 5. 管理端点

#### 5.1 提供商管理

**列出提供商**: `GET /admin/providers`

```bash
curl http://localhost:8000/admin/providers \
  -H "Authorization: Bearer YOUR_ADMIN_KEY"
```

**创建提供商**: `POST /admin/providers`

```bash
curl -X POST http://localhost:8000/admin/providers \
  -H "Authorization: Bearer YOUR_ADMIN_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "openai-primary",
    "type": "openai",
    "base_url": "https://api.openai.com/v1",
    "api_key": "sk-...",
    "enabled": true,
    "priority": 100,
    "weight": 100,
    "timeout": 60
  }'
```

**更新提供商**: `PATCH /admin/providers/{provider_id}`

```bash
curl -X PATCH http://localhost:8000/admin/providers/1 \
  -H "Authorization: Bearer YOUR_ADMIN_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "enabled": false
  }'
```

**删除提供商**: `DELETE /admin/providers/{provider_id}`

```bash
curl -X DELETE http://localhost:8000/admin/providers/1 \
  -H "Authorization: Bearer YOUR_ADMIN_KEY"
```

#### 5.2 健康状态

**系统健康**: `GET /admin/health`

```bash
curl http://localhost:8000/admin/health \
  -H "Authorization: Bearer YOUR_ADMIN_KEY"
```

**响应**:

```json
{
  "status": "healthy",
  "timestamp": "2025-01-01T00:00:00Z",
  "providers": [
    {
      "provider_id": 1,
      "provider_name": "openai-primary",
      "is_healthy": true,
      "response_time_ms": 123.45,
      "consecutive_failures": 0,
      "success_rate": 99.5
    }
  ],
  "database_status": "healthy",
  "cache_status": "healthy"
}
```

#### 5.3 统计信息

**系统统计**: `GET /admin/stats?hours=24`

```bash
curl http://localhost:8000/admin/stats?hours=24 \
  -H "Authorization: Bearer YOUR_ADMIN_KEY"
```

**响应**:

```json
{
  "total_requests": 10000,
  "successful_requests": 9950,
  "failed_requests": 50,
  "success_rate": 99.5,
  "avg_response_time_ms": 234.56,
  "providers": [
    {
      "provider_id": 1,
      "provider_name": "openai-primary",
      "total_requests": 8000,
      "successful_requests": 7960,
      "failed_requests": 40,
      "success_rate": 99.5,
      "avg_response_time_ms": 220.0,
      "total_tokens": 1000000,
      "total_cost": 20.00
    }
  ],
  "timestamp": "2025-01-01T00:00:00Z"
}
```

#### 5.4 请求日志

**查询日志**: `GET /admin/logs?page=1&page_size=50`

```bash
curl "http://localhost:8000/admin/logs?page=1&page_size=50&status_code=200" \
  -H "Authorization: Bearer YOUR_ADMIN_KEY"
```

## 使用示例

### Python完整示例

```python
import openai
from typing import Iterator

class LLMOrchestrator:
    def __init__(self, api_base: str, api_key: str):
        self.api_base = api_base
        self.api_key = api_key
        openai.api_base = api_base
        openai.api_key = api_key
    
    def chat(self, messages: list, **kwargs) -> dict:
        """发送聊天请求"""
        response = openai.ChatCompletion.create(
            messages=messages,
            **kwargs
        )
        return response
    
    def chat_stream(self, messages: list, **kwargs) -> Iterator[str]:
        """发送流式聊天请求"""
        response = openai.ChatCompletion.create(
            messages=messages,
            stream=True,
            **kwargs
        )
        
        for chunk in response:
            if chunk.choices[0].delta.get("content"):
                yield chunk.choices[0].delta.content

# 使用示例
client = LLMOrchestrator(
    api_base="http://localhost:8000/v1",
    api_key="your-api-key"
)

# 普通请求
response = client.chat(
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello!"}
    ],
    model="gpt-3.5-turbo",
    temperature=0.7
)
print(response.choices[0].message.content)

# 流式请求
for content in client.chat_stream(
    messages=[{"role": "user", "content": "Tell me a story."}],
    model="gpt-3.5-turbo"
):
    print(content, end="", flush=True)
```

### JavaScript/TypeScript示例

```typescript
import OpenAI from 'openai';

const client = new OpenAI({
  baseURL: 'http://localhost:8000/v1',
  apiKey: 'your-api-key',
});

// 普通请求
async function chat() {
  const response = await client.chat.completions.create({
    model: 'gpt-3.5-turbo',
    messages: [
      { role: 'user', content: 'Hello!' }
    ],
  });
  
  console.log(response.choices[0].message.content);
}

// 流式请求
async function chatStream() {
  const stream = await client.chat.completions.create({
    model: 'gpt-3.5-turbo',
    messages: [
      { role: 'user', content: 'Tell me a story.' }
    ],
    stream: true,
  });
  
  for await (const chunk of stream) {
    process.stdout.write(chunk.choices[0]?.delta?.content || '');
  }
}
```

### cURL示例集

```bash
# 基本聊天
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-3.5-turbo",
    "messages": [
      {"role": "user", "content": "What is the capital of France?"}
    ]
  }'

# 指定提供商
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-3.5-turbo",
    "messages": [{"role": "user", "content": "Hello"}],
    "provider": "openai-primary",
    "fallback_providers": ["openai-backup"]
  }'

# 流式响应
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-3.5-turbo",
    "messages": [{"role": "user", "content": "Count to 10"}],
    "stream": true
  }' \
  --no-buffer
```

## 错误处理

### 错误响应格式

```json
{
  "error": {
    "code": "error_code",
    "message": "Human readable error message",
    "details": {
      "request_id": "req_123",
      "additional_info": "..."
    }
  },
  "timestamp": "2025-01-01T00:00:00Z",
  "request_id": "req_123"
}
```

### 常见错误码

| HTTP状态码 | 错误码 | 说明 |
|-----------|--------|------|
| 400 | `invalid_request` | 请求参数无效 |
| 401 | `unauthorized` | 未提供API密钥或密钥无效 |
| 403 | `forbidden` | 权限不足 |
| 404 | `not_found` | 资源不存在 |
| 429 | `rate_limit_exceeded` | 超出速率限制 |
| 500 | `internal_error` | 内部服务器错误 |
| 503 | `service_unavailable` | 服务暂时不可用 |

### 错误处理示例

```python
import openai
from openai.error import (
    APIError,
    RateLimitError,
    AuthenticationError,
    InvalidRequestError
)

try:
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": "Hello"}]
    )
except AuthenticationError:
    print("认证失败,请检查API密钥")
except RateLimitError:
    print("超出速率限制,请稍后重试")
except InvalidRequestError as e:
    print(f"无效请求: {e}")
except APIError as e:
    print(f"API错误: {e}")
```

## 最佳实践

### 1. 错误重试

```python
import time
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10)
)
def chat_with_retry(messages):
    return openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=messages
    )
```

### 2. 超时设置

```python
# 设置请求超时
response = openai.ChatCompletion.create(
    model="gpt-3.5-turbo",
    messages=[{"role": "user", "content": "Hello"}],
    timeout=30  # 30秒超时
)
```

### 3. 流式响应处理

```python
def process_stream(messages):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=messages,
            stream=True
        )
        
        full_response = ""
        for chunk in response:
            content = chunk.choices[0].delta.get("content", "")
            full_response += content
            print(content, end="", flush=True)
        
        return full_response
    except Exception as e:
        print(f"\n错误: {e}")
        return None
```

### 4. 提供商故障转移

```python
# 指定主提供商和备用提供商
response = openai.ChatCompletion.create(
    model="gpt-3.5-turbo",
    messages=[{"role": "user", "content": "Hello"}],
    provider="openai-primary",
    fallback_providers=["openai-backup", "anthropic"]
)
```

### 5. 成本优化

```python
# 使用较便宜的模型进行简单任务
def choose_model(task_complexity):
    if task_complexity == "simple":
        return "gpt-3.5-turbo"
    elif task_complexity == "complex":
        return "gpt-4"
    else:
        return "gpt-3.5-turbo"

response = openai.ChatCompletion.create(
    model=choose_model("simple"),
    messages=[{"role": "user", "content": "Hello"}],
    max_tokens=100  # 限制token数量
)
```

### 6. 请求日志

```python
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def chat_with_logging(messages):
    logger.info(f"发送请求: {messages}")
    
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=messages
        )
        
        logger.info(f"响应成功, tokens: {response.usage.total_tokens}")
        return response
    except Exception as e:
        logger.error(f"请求失败: {e}")
        raise
```

## 性能优化

### 1. 连接池

```python
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

session = requests.Session()
retry = Retry(total=3, backoff_factor=0.3)
adapter = HTTPAdapter(max_retries=retry, pool_connections=10, pool_maxsize=20)
session.mount('http://', adapter)
session.mount('https://', adapter)

openai.requestssession = session
```

### 2. 批量请求

```python
import asyncio
import openai

async def chat_async(messages):
    return await openai.ChatCompletion.acreate(
        model="gpt-3.5-turbo",
        messages=messages
    )

async def batch_requests(messages_list):
    tasks = [chat_async(messages) for messages in messages_list]
    return await asyncio.gather(*tasks)

# 使用
messages_list = [
    [{"role": "user", "content": "Question 1"}],
    [{"role": "user", "content": "Question 2"}],
    [{"role": "user", "content": "Question 3"}]
]

responses = asyncio.run(batch_requests(messages_list))
```

## 监控和调试

### 查看请求ID

```python
response = openai.ChatCompletion.create(
    model="gpt-3.5-turbo",
    messages=[{"role": "user", "content": "Hello"}]
)

# 从响应头获取request_id
request_id = response.get("id")
print(f"Request ID: {request_id}")
```

### 性能分析

```python
import time

start = time.time()
response = openai.ChatCompletion.create(
    model="gpt-3.5-turbo",
    messages=[{"role": "user", "content": "Hello"}]
)
duration = time.time() - start

print(f"请求耗时: {duration:.2f}秒")
print(f"Tokens: {response.usage.total_tokens}")
print(f"提供商: {response.get('provider')}")
```

## 相关文档

- [部署指南](DEPLOYMENT.md)
- [架构文档](ARCHITECTURE.md)
- [项目README](../README.md)