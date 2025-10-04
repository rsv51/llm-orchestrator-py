# 使用示例

本目录包含了 LLM Orchestrator API 的各种使用示例,帮助您快速上手。

## 目录

- [Python 客户端示例](#python-客户端示例)
- [cURL 命令行示例](#curl-命令行示例)

## Python 客户端示例

### 运行示例

```bash
# 确保服务正在运行
# 然后执行:
cd examples
python client_example.py
```

### 示例内容

[`client_example.py`](client_example.py) 包含以下示例:

1. **基本聊天** - 展示如何发送简单的聊天请求
2. **流式聊天** - 展示如何处理流式响应
3. **多轮对话** - 展示如何维护对话上下文
4. **列出模型** - 展示如何获取可用模型列表
5. **自定义参数** - 展示如何使用温度、top_p 等参数

### 客户端类使用

```python
from client_example import LLMOrchestratorClient

# 初始化客户端
client = LLMOrchestratorClient(
    base_url="http://localhost:8000",
    api_key="your-api-key"
)

# 发送聊天请求
response = await client.chat_completion(
    messages=[
        {"role": "user", "content": "Hello!"}
    ],
    model="gpt-3.5-turbo"
)

# 获取模型列表
models = await client.list_models()
```

## cURL 命令行示例

### Linux/macOS

```bash
cd examples
chmod +x curl_examples.sh
./curl_examples.sh
```

### Windows

```cmd
cd examples
curl_examples.bat
```

### 示例内容

cURL 示例包含以下操作:

#### 基础操作

1. **健康检查**
```bash
curl http://localhost:8000/health
```

2. **获取模型列表**
```bash
curl -X GET http://localhost:8000/v1/models \
  -H "Authorization: Bearer test-key"
```

3. **基本聊天**
```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Authorization: Bearer test-key" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-3.5-turbo",
    "messages": [{"role": "user", "content": "Hello!"}]
  }'
```

4. **流式聊天**
```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Authorization: Bearer test-key" \
  -H "Content-Type: application/json" \
  -N \
  -d '{
    "model": "gpt-3.5-turbo",
    "messages": [{"role": "user", "content": "Count to 5"}],
    "stream": true
  }'
```

#### 管理操作

5. **获取提供商列表**
```bash
curl -X GET http://localhost:8000/admin/providers \
  -H "Authorization: Bearer admin-key"
```

6. **添加新提供商**
```bash
curl -X POST http://localhost:8000/admin/providers \
  -H "Authorization: Bearer admin-key" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "my-openai",
    "type": "openai",
    "api_key": "sk-xxx",
    "base_url": "https://api.openai.com/v1",
    "priority": 100,
    "enabled": true
  }'
```

7. **更新提供商**
```bash
curl -X PUT http://localhost:8000/admin/providers/1 \
  -H "Authorization: Bearer admin-key" \
  -H "Content-Type: application/json" \
  -d '{"enabled": false}'
```

8. **删除提供商**
```bash
curl -X DELETE http://localhost:8000/admin/providers/1 \
  -H "Authorization: Bearer admin-key"
```

9. **获取系统健康状态**
```bash
curl -X GET http://localhost:8000/admin/health \
  -H "Authorization: Bearer admin-key"
```

10. **获取请求统计**
```bash
curl -X GET http://localhost:8000/admin/stats?hours=24 \
  -H "Authorization: Bearer admin-key"
```

## 其他语言示例

### JavaScript/Node.js

```javascript
const axios = require('axios');

async function chatCompletion() {
  const response = await axios.post(
    'http://localhost:8000/v1/chat/completions',
    {
      model: 'gpt-3.5-turbo',
      messages: [
        { role: 'user', content: 'Hello!' }
      ]
    },
    {
      headers: {
        'Authorization': 'Bearer test-key',
        'Content-Type': 'application/json'
      }
    }
  );
  
  console.log(response.data);
}

chatCompletion();
```

### Go

```go
package main

import (
    "bytes"
    "encoding/json"
    "fmt"
    "net/http"
)

type Message struct {
    Role    string `json:"role"`
    Content string `json:"content"`
}

type ChatRequest struct {
    Model    string    `json:"model"`
    Messages []Message `json:"messages"`
}

func main() {
    reqBody := ChatRequest{
        Model: "gpt-3.5-turbo",
        Messages: []Message{
            {Role: "user", Content: "Hello!"},
        },
    }
    
    jsonData, _ := json.Marshal(reqBody)
    
    req, _ := http.NewRequest(
        "POST",
        "http://localhost:8000/v1/chat/completions",
        bytes.NewBuffer(jsonData),
    )
    
    req.Header.Set("Authorization", "Bearer test-key")
    req.Header.Set("Content-Type", "application/json")
    
    client := &http.Client{}
    resp, err := client.Do(req)
    if err != nil {
        panic(err)
    }
    defer resp.Body.Close()
    
    var result map[string]interface{}
    json.NewDecoder(resp.Body).Decode(&result)
    fmt.Println(result)
}
```

## 注意事项

1. **API 密钥**: 示例中使用的是默认测试密钥,生产环境请使用实际的 API 密钥
2. **基础 URL**: 默认为 `http://localhost:8000`,根据实际部署情况修改
3. **错误处理**: 生产代码应该包含完整的错误处理逻辑
4. **速率限制**: 注意 API 的速率限制设置

## 常见问题

### 连接被拒绝

确保服务正在运行:
```bash
# 检查服务状态
curl http://localhost:8000/health

# 如果未运行,启动服务
cd ..
python -m uvicorn app.main:app --reload
```

### 认证失败

检查 API 密钥配置:
```bash
# 查看 .env 文件中的密钥设置
cat ../.env
```

### 提供商不可用

检查提供商配置和密钥:
```bash
# 获取提供商状态
curl http://localhost:8000/admin/health \
  -H "Authorization: Bearer admin-key"
```

## 更多信息

- [完整 API 文档](../docs/API_USAGE.md)
- [部署指南](../docs/DEPLOYMENT.md)
- [架构说明](../docs/ARCHITECTURE.md)