# LLM Orchestrator 快速开始指南

本指南帮助您在 5 分钟内启动和使用 LLM Orchestrator。

## 前置要求

- Docker 和 Docker Compose (推荐)
- 或 Python 3.11+ (手动安装)

## 快速启动 (Docker)

### 1. 启动服务

```bash
# 克隆项目
git clone <repository-url>
cd llm-orchestrator-py

# 启动服务 (包括应用和 Redis)
docker-compose up -d

# 查看日志
docker-compose logs -f app
```

### 2. 验证服务

```bash
# 检查服务健康状态
curl http://localhost:8000/health

# 预期输出
# {"status":"healthy","service":"llm-orchestrator"}
```

### 3. 配置提供商

#### 方式 1: 使用 API (推荐)

```bash
# 添加 OpenAI 提供商
curl -X POST http://localhost:8000/admin/providers \
  -H "Content-Type: application/json" \
  -H "X-Admin-Key: your-admin-key" \
  -d '{
    "name": "openai-primary",
    "type": "openai",
    "api_key": "sk-your-openai-key",
    "enabled": true,
    "priority": 100,
    "weight": 100,
    "timeout": 60
  }'

# 添加 Anthropic 提供商
curl -X POST http://localhost:8000/admin/providers \
  -H "Content-Type: application/json" \
  -H "X-Admin-Key: your-admin-key" \
  -d '{
    "name": "anthropic-primary",
    "type": "anthropic",
    "api_key": "sk-ant-your-key",
    "enabled": true,
    "priority": 90,
    "weight": 50,
    "timeout": 60
  }'
```

#### 方式 2: 配置文件

编辑 `.env` 文件后重启服务。

### 4. 发送请求

```bash
# 基本聊天请求
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-api-key" \
  -d '{
    "model": "gpt-3.5-turbo",
    "messages": [
      {"role": "user", "content": "Hello, how are you?"}
    ]
  }'

# 流式请求
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-api-key" \
  -d '{
    "model": "gpt-3.5-turbo",
    "messages": [{"role": "user", "content": "Count to 10"}],
    "stream": true
  }' \
  --no-buffer
```

## Python 客户端示例

```python
import openai

# 配置客户端指向 LLM Orchestrator
openai.api_base = "http://localhost:8000/v1"
openai.api_key = "your-api-key"

# 发送请求
response = openai.ChatCompletion.create(
    model="gpt-3.5-turbo",
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "What is Python?"}
    ]
)

print(response.choices[0].message.content)

# 流式请求
for chunk in openai.ChatCompletion.create(
    model="gpt-3.5-turbo",
    messages=[{"role": "user", "content": "Tell me a story"}],
    stream=True
):
    content = chunk.choices[0].delta.get("content", "")
    print(content, end="", flush=True)
```

## 管理功能

### 查看提供商列表

```bash
curl http://localhost:8000/admin/providers \
  -H "X-Admin-Key: your-admin-key"
```

### 查看系统健康状态

```bash
curl http://localhost:8000/admin/health \
  -H "X-Admin-Key: your-admin-key"
```

### 查看统计信息

```bash
# 查看最近 24 小时的统计
curl http://localhost:8000/admin/stats?hours=24 \
  -H "X-Admin-Key: your-admin-key"
```

### 查看请求日志

```bash
# 查看最近的请求日志
curl "http://localhost:8000/admin/logs?page=1&page_size=10" \
  -H "X-Admin-Key: your-admin-key"
```

## 高级功能

### 1. 指定提供商

```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-api-key" \
  -d '{
    "model": "gpt-3.5-turbo",
    "messages": [{"role": "user", "content": "Hello"}],
    "provider": "openai-primary"
  }'
```

### 2. 配置故障转移

```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-api-key" \
  -d '{
    "model": "gpt-3.5-turbo",
    "messages": [{"role": "user", "content": "Hello"}],
    "provider": "openai-primary",
    "fallback_providers": ["openai-backup", "anthropic-primary"]
  }'
```

### 3. 自定义超时和重试

```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-api-key" \
  -d '{
    "model": "gpt-3.5-turbo",
    "messages": [{"role": "user", "content": "Hello"}],
    "timeout": 30,
    "retry_count": 5
  }'
```

## 访问 API 文档

开发环境下可以访问自动生成的 API 文档:

```bash
# Swagger UI
open http://localhost:8000/docs

# ReDoc
open http://localhost:8000/redoc
```

## 停止服务

```bash
# 停止服务
docker-compose stop

# 停止并删除容器
docker-compose down

# 停止并删除容器和数据卷
docker-compose down -v
```

## 常见问题

### Q: 如何更改端口?

编辑 `docker-compose.yml`:

```yaml
services:
  app:
    ports:
      - "8080:8000"  # 修改为 8080
```

### Q: 如何启用 MySQL?

1. 编辑 `.env`:

```env
DATABASE_TYPE=mysql
DATABASE_URL=mysql+aiomysql://user:pass@mysql:3306/dbname
```

2. 在 `docker-compose.yml` 添加 MySQL 服务

### Q: 如何查看详细日志?

```bash
# 查看应用日志
docker-compose logs -f app

# 查看 Redis 日志
docker-compose logs -f redis

# 查看所有日志
docker-compose logs -f
```

### Q: 如何备份数据?

```bash
# 备份 SQLite 数据库
docker cp llm-orchestrator:/app/data/llm_orchestrator.db ./backup.db

# 备份 Redis 数据
docker exec llm-orchestrator-redis redis-cli SAVE
docker cp llm-orchestrator-redis:/data/dump.rdb ./redis-backup.rdb
```

## 下一步

- 阅读 [完整文档](README.md)
- 查看 [API 使用指南](docs/API_USAGE.md)
- 了解 [部署最佳实践](docs/DEPLOYMENT.md)
- 探索 [系统架构](docs/ARCHITECTURE.md)

## 需要帮助?

- 查看文档: `docs/` 目录
- 提交 Issue: GitHub Issues
- 查看日志: `docker-compose logs -f`

## 许可证

[添加许可证信息]