# 数据库模型修复指南

## 🔍 问题诊断

### 错误信息
```
Failed to list providers: type object 'Provider' has no attribute 'priority'
```

### 根本原因
Provider 数据库模型缺少以下必需字段:
- `priority` - 优先级
- `weight` - 负载均衡权重
- `max_retries` - 最大重试次数
- `timeout` - 请求超时时间
- `rate_limit` - 速率限制

这些字段在 API Schema 中定义了,但数据库模型中缺失。

## 🔧 已应用的修复

### 1. 更新 Provider 模型
**文件**: `app/models/provider.py`

添加了缺失的字段:
```python
priority = Column(Integer, default=100, nullable=False)
weight = Column(Integer, default=100, nullable=False)
max_retries = Column(Integer, default=3, nullable=False)
timeout = Column(Integer, default=60, nullable=False)
rate_limit = Column(Integer)  # Optional
```

### 2. 创建数据库迁移
**文件**: `alembic/versions/002_add_provider_fields.py`

自动添加这些字段到现有数据库表。

### 3. 更新部署流程
**文件**: `scripts/docker-entrypoint.sh`

新的启动流程:
1. 等待数据库就绪
2. 自动运行数据库迁移
3. 初始化默认数据
4. 启动应用服务器

**文件**: `Dockerfile`

使用新的入口脚本,自动处理数据库更新。

## 📋 部署步骤

### 方式 A: 完全重建 (推荐 - 最干净)

```bash
# 1. 停止并删除所有容器和数据卷
docker-compose down -v

# 2. 重新构建并启动
docker-compose up -d --build

# 3. 查看启动日志
docker-compose logs -f app
```

### 方式 B: 保留数据的升级

```bash
# 1. 停止服务(不删除数据卷)
docker-compose stop

# 2. 重新构建镜像
docker-compose build

# 3. 启动服务(自动运行迁移)
docker-compose up -d

# 4. 查看迁移日志
docker-compose logs -f app
```

### 方式 C: 手动运行迁移

如果自动迁移失败,可以手动执行:

```bash
# 1. 进入容器
docker-compose exec app bash

# 2. 运行迁移
alembic upgrade head

# 3. 退出容器
exit

# 4. 重启服务
docker-compose restart app
```

## ✅ 验证修复

### 1. 检查日志
```bash
docker-compose logs -f app
```

期望看到:
```
🚀 Starting LLM Orchestrator...
⏳ Waiting for database...
✅ Database is ready!
📦 Running database migrations...
INFO  [alembic.runtime.migration] Running upgrade 001 -> 002, Add priority, weight, max_retries, timeout, rate_limit to Provider
🔧 Initializing database...
✅ Starting application server...
```

### 2. 测试 API
```bash
# 获取提供商列表
curl -H "Authorization: Bearer YOUR_ADMIN_KEY" \
     https://your-domain/admin/providers

# 应该返回 JSON 数组,不再报错
```

### 3. 测试 Web 界面
1. 访问 `https://your-domain/admin-ui/login.html`
2. 输入 Admin Key 登录
3. 查看"提供商管理"标签
4. 确认提供商列表正常显示

## 🔍 故障排查

### 问题 1: 迁移失败
**症状**: 看到 alembic 错误信息

**解决**:
```bash
# 检查当前迁移版本
docker-compose exec app alembic current

# 查看迁移历史
docker-compose exec app alembic history

# 如果需要重置数据库
docker-compose down -v
docker-compose up -d --build
```

### 问题 2: 数据库连接超时
**症状**: `Database connection failed`

**解决**:
```bash
# 检查数据库容器状态
docker-compose ps

# 查看数据库日志
docker-compose logs -f db

# 重启数据库
docker-compose restart db
```

### 问题 3: 权限错误
**症状**: `Permission denied`

**解决**:
```bash
# 给脚本添加执行权限
chmod +x llm-orchestrator-py/scripts/docker-entrypoint.sh

# 重新构建
docker-compose build
```

## 📝 字段说明

### priority (优先级)
- **类型**: Integer
- **默认值**: 100
- **说明**: 值越高优先级越高,系统会优先使用高优先级提供商
- **范围**: 0-1000

### weight (权重)
- **类型**: Integer  
- **默认值**: 100
- **说明**: 负载均衡权重,权重越高分配的请求越多
- **范围**: 0-1000

### max_retries (最大重试)
- **类型**: Integer
- **默认值**: 3
- **说明**: 请求失败时的最大重试次数
- **范围**: 0-10

### timeout (超时时间)
- **类型**: Integer
- **默认值**: 60
- **说明**: 单个请求的超时时间(秒)
- **范围**: 1-300

### rate_limit (速率限制)
- **类型**: Integer (可选)
- **默认值**: None
- **说明**: 每分钟最大请求数,不设置表示无限制
- **范围**: >= 1

## 🎯 后续改进建议

1. **添加数据验证**
   - 在 API 层添加字段范围验证
   - 防止设置不合理的值

2. **改进错误处理**
   - 提供更友好的错误消息
   - 添加字段级别的错误提示

3. **完善文档**
   - 在 Web 界面添加字段说明
   - 提供配置最佳实践指南

4. **监控和告警**
   - 记录配置变更历史
   - 异常配置自动告警

## 📚 相关文档

- [项目架构](docs/ARCHITECTURE.md)
- [快速开始](QUICKSTART.md)
- [API 文档](docs/API.md)
- [部署指南](README.md)