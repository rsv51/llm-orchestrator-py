# LLM Orchestrator 架构设计文档

## 项目概述

LLM Orchestrator 是一个基于 Python 的企业级多服务商 LLM API 代理服务,综合了 llmio-master 和 OrchestrationApi-main 两个项目的优势特性。

## 技术架构

### 核心技术栈

- **Web 框架**: FastAPI 0.104+ - 提供异步支持和自动 API 文档
- **数据库**: SQLAlchemy 2.0+ ORM - 支持 SQLite 和 MySQL
- **缓存**: Redis 7.0+ - 配置缓存和健康状态缓存
- **日志**: structlog - 结构化日志记录
- **HTTP 客户端**: httpx - 异步 HTTP 和连接池支持
- **配置管理**: Pydantic Settings - 类型安全的配置

### 项目结构

```
llm-orchestrator-py/
├── app/                      # 应用主目录
│   ├── core/                # 核心模块
│   │   ├── config.py        # 配置管理 ✓
│   │   ├── database.py      # 数据库连接
│   │   ├── cache.py         # Redis 缓存
│   │   └── logger.py        # 日志配置
│   ├── models/              # 数据库模型
│   │   ├── provider.py      # 提供商模型
│   │   ├── model.py         # 模型配置
│   │   ├── request_log.py   # 请求日志
│   │   └── health.py        # 健康状态
│   ├── schemas/             # Pydantic 模式
│   ├── providers/           # 提供商实现
│   │   ├── base.py          # 抽象基类
│   │   ├── openai.py        # OpenAI
│   │   ├── anthropic.py     # Anthropic
│   │   └── gemini.py        # Gemini
│   ├── services/            # 业务服务
│   │   ├── router.py        # 请求路由
│   │   ├── balancer.py      # 负载均衡
│   │   ├── health_check.py  # 健康检查
│   │   └── logger.py        # 日志服务
│   ├── api/                 # API 路由
│   └── main.py              # 应用入口
├── config/                  # 配置文件
├── docker/                  # Docker 相关 ✓
└── docs/                    # 文档
```

## 核心功能模块

### 1. 配置管理 (✓ 已完成)

- 基于 Pydantic Settings 的类型安全配置
- 支持环境变量和 .env 文件
- 配置项包括:应用、数据库、Redis、日志、健康检查等

### 2. 数据库层

**设计要点:**
- Provider 表 - 提供商配置
- Model 表 - 模型配置  
- ModelProvider 表 - 多对多关联,支持权重和特性
- RequestLog 表 - 请求日志(带索引优化)
- ProviderHealth 表 - 健康状态
- ProviderStats 表 - 使用统计

### 3. 提供商抽象层

**设计模式:**
- BaseProvider 抽象基类定义统一接口
- 各提供商实现类(OpenAI、Anthropic、Gemini)
- 工厂模式创建提供商实例
- 支持透明代理模式

### 4. 智能路由与负载均衡

**核心特性:**
- 加权随机算法(借鉴 llmio)
- 健康状态筛选
- 模型别名映射
- 参数覆盖
- 多级故障转移(API密钥 → 提供商)

### 5. 健康检查机制

**检查策略:**
- 主动检查 - 定时调用提供商 API
- 被动检查 - 基于请求结果更新状态
- 三级状态 - healthy/degraded/unhealthy
- 自动恢复 - 连续成功后恢复健康
- 智能重试 - 不健康提供商延迟重试

### 6. API 设计

**兼容性:**
- OpenAI API 格式 - /v1/chat/completions
- Anthropic 原生格式 - /v1/messages
- Gemini 原生格式
- 管理 API - 完整的 CRUD 操作

### 7. 性能优化

**优化策略:**
- 异步 IO - FastAPI + httpx 异步架构
- 连接池 - HTTP 连接复用
- 配置缓存 - Redis 缓存减少数据库查询
- 批量操作 - 支持批量 CRUD
- 数据库索引 - 优化常用查询

### 8. Docker 部署 (✓ 已完成)

**特性:**
- 多阶段构建 - 减小镜像体积
- 非 root 用户 - 提高安全性
- 健康检查 - 自动监控服务状态
- docker-compose - 一键部署应用和 Redis
- 数据持久化 - 挂载卷支持

## 已完成的工作

### 基础设施 ✓
1. 项目结构创建
2. Docker 配置(Dockerfile + docker-compose.yml)
3. 依赖管理(requirements.txt)
4. 环境配置(.env.example)
5. Git 配置(.gitignore)
6. 核心配置模块(app/core/config.py)

### 待实现模块

1. **核心模块**
   - [ ] database.py - 数据库连接和会话管理
   - [ ] cache.py - Redis 缓存封装
   - [ ] logger.py - 结构化日志配置

2. **数据模型**
   - [ ] Provider、Model、ModelProvider 等数据库模型
   - [ ] Pydantic schemas 定义

3. **提供商实现**
   - [ ] BaseProvider 抽象基类
   - [ ] OpenAI、Anthropic、Gemini 实现

4. **业务服务**
   - [ ] 请求路由器
   - [ ] 负载均衡器
   - [ ] 健康检查服务
   - [ ] 请求日志服务

5. **API 路由**
   - [ ] v1 API(聊天完成、模型列表)
   - [ ] 管理 API(CRUD 操作)

6. **应用入口**
   - [ ] main.py - FastAPI 应用配置

## 与原项目的对比

### 相比 llmio-master

**继承的优势:**
- ✓ 配置缓存机制
- ✓ 健康检查系统
- ✓ 批量操作支持
- ✓ 加权负载均衡

**改进之处:**
- 使用 Python 生态,更易维护
- 更好的类型提示支持
- 异步架构性能更优

### 相比 OrchestrationApi-main

**继承的优势:**
- ✓ 多提供商智能路由
- ✓ 故障转移机制
- ✓ 透明代理模式
- ✓ 企业级功能

**改进之处:**
- 模块化架构更清晰
- 配置管理更灵活
- 代码复用性更好

## 设计原则

1. **模块化** - 清晰的模块划分,低耦合高内聚
2. **可扩展** - 易于添加新提供商和功能
3. **高性能** - 异步 IO,连接池,缓存优化
4. **易维护** - 类型提示,结构化日志,清晰文档
5. **生产就绪** - Docker 支持,健康检查,监控

## 下一步计划

按优先级排序:

1. 实现数据库模型和连接管理
2. 实现提供商抽象层和具体实现
3. 实现核心业务服务(路由、负载均衡)
4. 实现 API 路由和控制器
5. 实现健康检查服务
6. 完善日志和监控
7. 编写测试用例
8. 完善文档

## 参考资料

- llmio-master: Go 语言实现的 LLM 代理服务
- OrchestrationApi-main: C# 实现的企业级多提供商代理
- FastAPI 文档: https://fastapi.tiangolo.com/
- SQLAlchemy 文档: https://docs.sqlalchemy.org/