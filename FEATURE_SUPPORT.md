# LLM Orchestrator 功能支持文档

本文档说明 llm-orchestrator-py 项目对工具调用、结构化输出、视觉输入等高级功能的支持情况。

## ✅ 已支持的功能

### 1. 工具调用 (Tool Calling / Function Calling)

**Schema 支持**: ✅ 完整支持

- [`FunctionDefinition`](app/api/schemas.py:47-51) - 函数定义
- [`ToolDefinition`](app/api/schemas.py:54-57) - 工具定义
- [`ChatCompletionRequest`](app/api/schemas.py:74-77) 支持:
  - `tools`: 工具列表
  - `tool_choice`: 工具选择策略
  - `functions`: 传统函数调用(向后兼容)
  - `function_call`: 传统函数选择(向后兼容)
- [`ChatMessage`](app/api/schemas.py:42-44) 支持:
  - `tool_calls`: 工具调用结果
  - `tool_call_id`: 工具调用ID
  - `function_call`: 传统函数调用结果

**Provider 实现**:
- ✅ **OpenAI Provider** - 完整支持,直接透传 `tools` 和 `tool_choice` 参数
- ⚠️ **Anthropic Provider** - 需要格式转换(Claude 使用不同的工具调用格式)
- ⚠️ **Gemini Provider** - 需要格式转换(Gemini 使用不同的工具调用格式)

**数据库配置**:
- [`ModelProviderBase.tool_call`](app/api/schemas.py:351) - 每个模型-供应商映射可以独立配置是否支持工具调用

**使用示例**:
```python
{
  "model": "gpt-4",
  "messages": [...],
  "tools": [
    {
      "type": "function",
      "function": {
        "name": "get_weather",
        "description": "获取天气信息",
        "parameters": {
          "type": "object",
          "properties": {
            "location": {"type": "string"}
          }
        }
      }
    }
  ],
  "tool_choice": "auto"
}
```

---

### 2. 结构化输出 (Structured Output / JSON Mode)

**Schema 支持**: ✅ 完整支持

- [`ChatCompletionRequest.response_format`](app/api/schemas.py:78) - 响应格式控制

**Provider 实现**:
- ✅ **OpenAI Provider** - 完整支持,直接透传 `response_format` 参数
- ⚠️ **Anthropic Provider** - 部分支持(需要通过 system prompt 引导)
- ⚠️ **Gemini Provider** - 部分支持(需要通过 system prompt 引导)

**数据库配置**:
- [`ModelProviderBase.structured_output`](app/api/schemas.py:352) - 每个模型-供应商映射可以独立配置是否支持结构化输出

**使用示例**:
```python
{
  "model": "gpt-4o",
  "messages": [...],
  "response_format": {
    "type": "json_object"
  }
}
```

或使用 JSON Schema:
```python
{
  "model": "gpt-4o",
  "messages": [...],
  "response_format": {
    "type": "json_schema",
    "json_schema": {
      "name": "user_info",
      "schema": {
        "type": "object",
        "properties": {
          "name": {"type": "string"},
          "age": {"type": "integer"}
        },
        "required": ["name", "age"]
      }
    }
  }
}
```

---

### 3. 视觉输入 (Vision / Image Input)

**Schema 支持**: ✅ 基础支持

- [`ChatMessage.content`](app/api/schemas.py:40) 可以是字符串或多模态内容数组

**数据库配置**:
- [`ModelProviderBase.image`](app/api/schemas.py:353) - 每个模型-供应商映射可以独立配置是否支持图像输入

**Provider 实现**:
- ✅ **OpenAI Provider** - 支持(gpt-4-vision, gpt-4o 等模型)
- ✅ **Anthropic Provider** - 支持(Claude 3 系列模型)
- ✅ **Gemini Provider** - 支持(gemini-pro-vision, gemini-1.5-pro 等模型)

**使用示例**:
```python
{
  "model": "gpt-4o",
  "messages": [
    {
      "role": "user",
      "content": [
        {"type": "text", "text": "这张图片里有什么?"},
        {
          "type": "image_url",
          "image_url": {
            "url": "https://example.com/image.jpg"
          }
        }
      ]
    }
  ]
}
```

或使用 base64 编码:
```python
{
  "type": "image_url",
  "image_url": {
    "url": "data:image/jpeg;base64,/9j/4AAQSkZJRg..."
  }
}
```

---

## 📋 请求参数完整支持列表

### 基础参数
- ✅ `model` - 模型名称
- ✅ `messages` - 消息列表
- ✅ `temperature` - 温度参数 (0-2)
- ✅ `top_p` - 核采样参数 (0-1)
- ✅ `max_tokens` - 最大令牌数
- ✅ `stop` - 停止序列
- ✅ `stream` - 流式输出
- ✅ `user` - 用户标识

### 高级参数
- ✅ `presence_penalty` - 存在惩罚 (-2 到 2)
- ✅ `frequency_penalty` - 频率惩罚 (-2 到 2)
- ✅ `logit_bias` - Logit 偏置
- ✅ `seed` - 随机种子

### 功能参数
- ✅ `tools` - 工具定义列表
- ✅ `tool_choice` - 工具选择策略
- ✅ `response_format` - 响应格式(JSON模式)
- ✅ `functions` - 传统函数定义(向后兼容)
- ✅ `function_call` - 传统函数调用(向后兼容)

### 编排参数(自定义)
- ✅ `provider` - 指定供应商
- ✅ `fallback_providers` - 备用供应商列表
- ✅ `timeout` - 请求超时时间
- ✅ `retry_count` - 重试次数

---

## 🔧 配置建议

### 1. 为支持工具调用的模型配置

在管理界面的"模型-供应商映射"中:
- 勾选 `tool_call` - 表示该模型支持工具调用
- 示例: `gpt-4`, `gpt-4-turbo`, `gpt-4o`, `claude-3-opus`, `claude-3-sonnet`

### 2. 为支持结构化输出的模型配置

在管理界面的"模型-供应商映射"中:
- 勾选 `structured_output` - 表示该模型支持结构化输出
- 示例: `gpt-4o`, `gpt-4-turbo`, 所有 GPT-4 系列

### 3. 为支持视觉输入的模型配置

在管理界面的"模型-供应商映射"中:
- 勾选 `image` - 表示该模型支持图像输入
- 示例: `gpt-4o`, `gpt-4-vision-preview`, `claude-3-opus`, `claude-3-sonnet`, `gemini-pro-vision`, `gemini-1.5-pro`

---

## ⚠️ 注意事项

### OpenAI Provider
- 完全兼容 OpenAI API,所有参数直接透传
- 工具调用、结构化输出、视觉输入均原生支持

### Anthropic Provider
- 工具调用使用 Anthropic 专有格式,需要格式转换
- 结构化输出通过 system prompt 引导实现
- 视觉输入使用 base64 编码格式

### Gemini Provider
- 工具调用使用 Function Calling API
- 结构化输出通过 generation_config 配置
- 视觉输入支持 inline_data 和 file_data 格式

---

## 📊 功能矩阵

| 功能 | OpenAI | Anthropic | Gemini |
|------|--------|-----------|--------|
| 工具调用 | ✅ 原生 | ⚠️ 需转换 | ⚠️ 需转换 |
| 结构化输出 | ✅ 原生 | ⚠️ Prompt引导 | ⚠️ Config配置 |
| 视觉输入 | ✅ 原生 | ✅ 原生 | ✅ 原生 |
| 流式输出 | ✅ | ✅ | ✅ |
| 函数调用(旧) | ✅ | ❌ | ❌ |

---

## 🔄 版本历史

### v1.0.0 (2025-10-04)
- ✅ 修复 Provider 方法签名,统一使用 `ChatCompletionRequest`
- ✅ OpenAI Provider 完整支持工具调用和结构化输出
- ✅ 所有 Provider 统一使用 `ProviderConfig` 初始化
- ✅ 数据库模型支持 `tool_call`, `structured_output`, `image` 配置字段
- ✅ 完整的参数传递链路: Request → Router → Provider → API

---

## 📝 开发建议

如需添加对 Anthropic 和 Gemini 工具调用的完整支持,需要在各自的 Provider 中实现格式转换:

1. **Anthropic**: 在 [`AnthropicProvider._convert_to_anthropic_format`](app/providers/anthropic.py:138-186) 中添加 tools 转换
2. **Gemini**: 在 [`GeminiProvider._convert_to_gemini_format`](app/providers/gemini.py:141-201) 中添加 tools 转换

参考资料:
- [OpenAI Function Calling](https://platform.openai.com/docs/guides/function-calling)
- [Anthropic Tool Use](https://docs.anthropic.com/claude/docs/tool-use)
- [Google Gemini Function Calling](https://ai.google.dev/docs/function_calling)