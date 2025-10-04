# LLM Orchestrator

一个基于 Python 的企业级多服务商 LLM API 代理服务，提供统一的 OpenAI 兼容接口，支持智能路由、故障转移、负载均衡等企业级功能。

## 核心特性

### 多服务商支持
- **OpenAI**: 支持 GPT-3.5、GPT-4 等全系列模型
- **Anthropic Claude**: 支持 Claude 3/3.5 系列模型
- **Google Gemini**: 支持 Gemini Pro、Flash 等模型
- **可扩展架构**: 易于添加更多 AI 服务商

### 智能路由与负载均衡
- **加权随机算法**: 基于权重的智能负载分配
- **健康状态筛选**: 自动过滤不健康的提供商
- **多级故障转移**: 支持 API 密钥级别和提供商级别的故障转移
- **模型别名映射**: 灵活的模型名称映射
- **参数覆盖**: 支持全局和提供商级别的参数覆盖

### 健康检查与监控
- **主动健康检查**: 定时检测提供商状态
- **被动健康检查**: 基于请求结果自动更新健康状态
- **健康状态分级**: healthy/degraded/unhealthy 三级状态
- **自动恢复机制**: 连续成功后自动恢复健康状态
- **智能重试**: 不健康的提供商延迟重试

### 性能优化
- **异步 IO**: 基于 FastAPI 和 httpx 的高并发异步架构
- **连接池管理**: HTTP 连接复用，减少连接开销
- **配置缓存**: Redis 缓存提供商配置，减少数据库查询
- **批量操作**: 支持批量创建/删除/更新
- **数据库索引**: 优化的数据库索引设计

### 完整的管理功能
- **RESTful API**: 完整的提供商和模型管理接口
- **请求日志**: 详细的请求统计和日志记录
- **使用统计**: 提供商使用情况统计分析
- **配置导入导出**: 支持配置的备份和迁移
- **批量操作**: 批量删除、批量更新等操作

## 技术栈

- **Web 框架**: FastAPI 0.104+ (异步支持、自动 API 文档)
- **数据库**: SQLAlchemy 2.0+ ORM + SQLite/MySQL
- **缓存**: Redis 7.0+ (配置缓存、健康状态缓存)
- **日志**: structlog (结构化日志)
- **HTTP 客户端**: httpx (异步 HTTP，连接池支持)
- **配置管理**: Pydantic Settings (类型安全的配置)

## 快速开始

### 使用 Docker Compose (推荐)

```bash
# 克隆项目
git clone <repository-url>
cd llm-orchestrator-py

# 启动服务
docker-compose up -d

# 查看日志
docker-compose logs -f
```

### 本地开发

```bash
# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 文件设置配置

# 初始化数据库
python -m app.core.database init

# 启动服务
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

服务启动后访问:
- API 文档: http://localhost:8000/docs
- 健康检查: http://localhost:8000/health
- 管理 API: http://localhost:8000/api/

## 配置说明

### 环境变量

```bash
# 应用配置
APP_NAME=llm-orchestrator
APP_HOST=0.0.0.0
APP_PORT=8000
APP_ENV=production

# 认证
AUTH_TOKEN=your-secret-token

# 数据库
DATABASE_TYPE=sqlite  # sqlite 或 mysql
DATABASE_URL=sqlite:///./data/llm_orchestrator.db
# MySQL 示例: mysql+asyncmy://user:pass@localhost/dbname

# Redis
REDIS_URL=redis://localhost:6379/0
REDIS_ENABLED=true

# 日志
LOG_LEVEL=INFO
LOG_FILE=./logs/app.log

# 健康检查
HEALTH_CHECK_ENABLED=true
HEALTH_CHECK_INTERVAL=300  # 5分钟
HEALTH_CHECK_MAX_ERRORS=5
HEALTH_CHECK_RETRY_HOURS=1
```

## API 使用指南

### 聊天完成 API (OpenAI 兼容)

```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Authorization: Bearer your-token" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-3.5-turbo",
    "messages": [
      {"role": "user", "content": "Hello!"}
    ],
    "stream": false
  }'
```

### Anthropic 原生 API

```bash
curl -X POST http://localhost:8000/v1/messages \
  -H "Authorization: Bearer your-token" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "claude-3-sonnet-20240229",
    "max_tokens": 1024,
    "messages": [
      {"role": "user", "content": "Hello!"}
    ]
  }'
```

### 管理 API

```bash
# 获取所有提供商
curl http://localhost:8000/api/providers \
  -H "Authorization: Bearer your-token"

# 创建提供商
curl -X POST http://localhost:8000/api/providers \
  -H "Authorization: Bearer your-token" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "OpenAI",
    "type": "openai",
    "config": {
      "base_url": "https://api.openai.com/v1",
      "api_key": "sk-..."
    }
  }'

# 获取健康状态
curl http://localhost:8000/api/providers/health \
  -H "Authorization: Bearer your-token"
```

## 项目结构

```
llm-orchestrator-py/
├── app/                      # 应用主目录
│   ├── __init__.py
│   ├── main.py              # FastAPI 应用入口
│   ├── core/                # 核心模块
│   │   ├── config.py        # 配置管理
│   │   ├── database.py      # 数据库连接
│   │   ├── cache.py         # Redis 缓存
│   │   └── logger.py        # 日志配置
│   ├── models/              # 数据库模型
│   │   ├── provider.py      # 提供商模型
│   │   ├── model.py         # 模型配置
│   │   ├── request_log.py   # 请求日志
│   │   └── health.py        # 健康状态
│   ├── schemas/             # Pydantic 模式
│   │   ├── provider.py
│   │   ├── chat.py
│   │   └── response.py
│   ├── providers/           # 提供商实现
│   │   ├── base.py          # 抽象基类
│   │   ├── openai.py        # OpenAI 实现
│   │   ├── anthropic.py     # Anthropic 实现
│   │   └── gemini.py        # Gemini 实现
│   ├── services/            # 业务服务
│   │   ├── router.py        # 请求路由器
│   │   ├── balancer.py      # 负载均衡器
│   │   ├── health_check.py  # 健康检查服务
│   │   └── logger.py        # 请求日志服务
│   ├── api/                 # API 路由
│   │   ├── v1/              # v1 版本 API
│   │   └── admin/           # 管理 API
│   ├── middleware/          # 中间件
│   │   ├── auth.py          # 认证中间件
│   │   └── error.py         # 错误处理
│   └── utils/               # 工具函数
├── config/                  # 配置文件
├── tests/                   # 测试
├── docs/                    # 文档
├── docker/                  # Docker 相关
├── scripts/                 # 脚本
├── requirements.txt         # Python 依赖
├── Dockerfile              # Docker 镜像
├── docker-compose.yml      # Docker Compose
└── README.md               # 项目说明
```

## 开发指南

### 添加新的提供商

1. 在 `app/providers/` 创建新的提供商实现
2. 继承 `BaseProvider` 抽象类
3. 实现必要的方法
4. 在 `app/providers/factory.py` 注册提供商

### 运行测试

```bash
# 运行所有测试
pytest

# 运行特定测试
pytest tests/test_providers.py

# 生成覆盖率报告
pytest --cov=app tests/
```

## 部署

### Docker 部署

```bash
# 构建镜像
docker build -t llm-orchestrator:latest .

# 运行容器
docker run -d \
  -p 8000:8000 \
  -e AUTH_TOKEN=your-token \
  -v ./data:/app/data \
  -v ./logs:/app/logs \
  llm-orchestrator:latest
```

### 生产环境建议

- 使用 MySQL 而非 SQLite
- 启用 Redis 缓存
- 配置日志轮转
- 设置资源限制
- 配置反向代理 (Nginx)
- 启用 HTTPS

## 监控与维护

### 健康检查

```bash
# 检查服务状态
curl http://localhost:8000/health

# 检查提供商健康状态
curl http://localhost:8000/api/providers/health \
  -H "Authorization: Bearer your-token"
```

### 日志查看

```bash
# 查看应用日志
tail -f logs/app.log

# 查看请求日志
curl http://localhost:8000/api/logs \
  -H "Authorization: Bearer your-token"
```

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！

## 联系方式

- GitHub Issues: [项目 Issues](https://github.com/your-repo/issues)
- 邮箱: your-email@example.com