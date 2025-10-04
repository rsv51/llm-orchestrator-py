# Docker 部署指南

## 概述

本项目使用 Alembic 进行数据库迁移管理。Docker 容器启动时会自动执行所有待应用的数据库迁移,确保数据库结构始终与代码同步。

## 数据持久化

### 关键原则

**数据库文件必须挂载到宿主机卷**,否则每次容器重启数据都会丢失。

```yaml
# docker-compose.yml
volumes:
  - ./data:/app/data  # 挂载数据目录
```

这样确保:
- ✅ 数据库文件保存在宿主机 `./data` 目录
- ✅ 容器重启/重建后数据不会丢失
- ✅ 迁移只需执行一次

## 自动迁移机制

### 工作流程

1. **容器启动** → 执行 `docker-entrypoint.sh`
2. **自动迁移** → 运行 `alembic upgrade head`
3. **启动应用** → 启动 FastAPI 服务

```bash
# scripts/docker-entrypoint.sh
echo "📦 Running database migrations..."
alembic upgrade head

echo "✅ Starting application server..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Alembic 迁移版本

项目包含以下迁移版本:

| 版本 | 文件 | 描述 |
|------|------|------|
| 001 | `001_initial_schema.py` | 创建初始数据库表结构 |
| 002 | `002_add_provider_fields.py` | 添加 Provider 扩展字段 |
| 003 | `003_provider_config_to_fields.py` | Provider 配置重构 |
| **004** | `004_add_provider_health_fields.py` | **添加 ProviderHealth 缺失字段** |

最新的 `004` 版本解决了健康检查问题,添加了:
- `response_time_ms` - 响应时间
- `error_message` - 错误消息
- `last_check` - 最后检查时间
- `consecutive_failures` - 连续失败次数
- `success_rate` - 成功率

## 部署场景

### 场景 1: 全新部署

**第一次部署项目**:

```bash
# 1. 构建镜像
docker-compose build

# 2. 启动容器
docker-compose up -d

# 自动执行:
# - 创建数据库文件
# - 运行所有迁移 (001 → 002 → 003 → 004)
# - 启动应用
```

**结果**: 数据库结构完整,包含所有必需字段。

### 场景 2: 代码更新重新部署

**已有数据库,更新代码后重新部署**:

```bash
# 1. 拉取最新代码
git pull origin main

# 2. 重新构建镜像
docker-compose build

# 3. 重启容器
docker-compose up -d

# 自动执行:
# - 检测数据库已存在
# - 只运行未应用的新迁移 (例如 004)
# - 启动应用
```

**关键**: 由于数据库挂载在宿主机卷,数据不会丢失,Alembic 会智能识别并只执行新的迁移。

### 场景 3: 容器重启(无代码更改)

**仅重启容器**:

```bash
docker-compose restart
# 或
docker-compose down && docker-compose up -d

# 自动执行:
# - 检测所有迁移已应用
# - 跳过迁移步骤
# - 直接启动应用
```

**原因**: Alembic 在数据库中维护 `alembic_version` 表,记录已应用的迁移版本。

## Docker Compose 配置

### 完整示例

```yaml
# docker-compose.yml
version: '3.8'

services:
  llm-orchestrator:
    build: .
    container_name: llm-orchestrator
    ports:
      - "8000:8000"
    volumes:
      # 数据持久化 - 必需
      - ./data:/app/data
      # 日志持久化 - 可选
      - ./logs:/app/logs
      # 配置文件 - 可选
      - ./.env:/app/.env:ro
    environment:
      # 数据库配置
      DATABASE_URL: sqlite:////app/data/llm_orchestrator.db
      # 日志配置
      LOG_LEVEL: INFO
      LOG_FILE: /app/logs/app.log
      # Admin 密钥
      ADMIN_KEY: your-secret-admin-key
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

volumes:
  # 如果使用命名卷
  app_data:
    driver: local
  app_logs:
    driver: local
```

### 环境变量

```bash
# .env 文件示例
DATABASE_URL=sqlite:////app/data/llm_orchestrator.db
ADMIN_KEY=your-secret-admin-key-here
LOG_LEVEL=INFO
LOG_FILE=/app/logs/app.log

# Redis (可选)
REDIS_ENABLED=false
REDIS_URL=redis://redis:6379/0
```

## 验证部署

### 1. 检查容器状态

```bash
docker-compose ps

# 预期输出:
NAME                 STATUS          PORTS
llm-orchestrator    Up (healthy)    0.0.0.0:8000->8000/tcp
```

### 2. 查看启动日志

```bash
docker-compose logs -f llm-orchestrator

# 预期看到:
# 🚀 Starting LLM Orchestrator...
# 📦 Running database migrations...
# INFO  [alembic.runtime.migration] Context impl SQLiteImpl.
# INFO  [alembic.runtime.migration] Will assume non-transactional DDL.
# INFO  [alembic.runtime.migration] Running upgrade 003 -> 004, Add missing provider_health fields
# ✅ Starting application server...
# INFO:     Started server process [1]
# INFO:     Waiting for application startup.
# INFO:     Application startup complete.
```

### 3. 验证数据库迁移

```bash
# 进入容器
docker exec -it llm-orchestrator bash

# 检查迁移版本
alembic current

# 预期输出:
004 (head)

# 检查数据库表结构
sqlite3 /app/data/llm_orchestrator.db

sqlite> .schema provider_health
-- 应该包含所有字段: response_time_ms, error_message, last_check, etc.
```

### 4. 测试健康检查 API

```bash
curl -H "Authorization: Bearer YOUR_ADMIN_KEY" \
  http://localhost:8000/api/admin/health

# 预期返回:
{
  "status": "healthy",
  "providers": [...],
  "database_status": "healthy"
}
```

## 故障排除

### 问题 1: 迁移失败

**症状**:
```
ERROR [alembic.util.messaging] Target database is not up to date.
```

**解决**:
```bash
# 手动进入容器执行迁移
docker exec -it llm-orchestrator alembic upgrade head

# 查看迁移历史
docker exec -it llm-orchestrator alembic history
```

### 问题 2: 数据库文件权限错误

**症状**:
```
sqlite3.OperationalError: unable to open database file
```

**解决**:
```bash
# 宿主机上检查目录权限
ls -la ./data

# 确保容器用户有写权限
chmod 755 ./data
chown 1000:1000 ./data  # 容器内 appuser 的 UID/GID
```

### 问题 3: 健康检查失败

**症状**:
```
no such column: provider_health.response_time_ms
```

**原因**: 迁移 004 未执行

**解决**:
```bash
# 1. 检查当前迁移版本
docker exec -it llm-orchestrator alembic current

# 2. 如果不是 004,手动升级
docker exec -it llm-orchestrator alembic upgrade head

# 3. 重启容器
docker-compose restart
```

### 问题 4: 数据丢失

**症状**: 每次重启后数据都重置

**原因**: 数据库未挂载到宿主机卷

**解决**:
```yaml
# 检查 docker-compose.yml
volumes:
  - ./data:/app/data  # 必须配置此行

# 如果已经丢失数据,只能重新配置
```

## 回滚迁移

如果新迁移导致问题,可以回滚:

```bash
# 回滚到上一个版本
docker exec -it llm-orchestrator alembic downgrade -1

# 回滚到特定版本
docker exec -it llm-orchestrator alembic downgrade 003

# 查看可用的回滚版本
docker exec -it llm-orchestrator alembic history
```

## 生产环境建议

### 1. 数据备份

**自动备份**:
```bash
# 创建备份脚本
#!/bin/bash
# backup_db.sh
BACKUP_DIR="/backup/llm-orchestrator"
DATE=$(date +%Y%m%d_%H%M%S)
docker exec llm-orchestrator sqlite3 /app/data/llm_orchestrator.db ".backup /app/data/backup_${DATE}.db"
cp ./data/backup_${DATE}.db ${BACKUP_DIR}/

# 定时任务
0 2 * * * /path/to/backup_db.sh
```

### 2. 健康监控

```yaml
# docker-compose.yml - 添加监控
services:
  llm-orchestrator:
    # ... 其他配置
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
    
  # 可选: 添加监控工具
  prometheus:
    image: prom/prometheus
    # ...
```

### 3. 更新流程

**推荐的生产环境更新流程**:

1. **备份数据库**
   ```bash
   docker exec llm-orchestrator sqlite3 /app/data/llm_orchestrator.db ".backup /app/data/backup_before_update.db"
   ```

2. **拉取代码**
   ```bash
   git pull origin main
   ```

3. **查看新迁移**
   ```bash
   # 检查是否有新的迁移文件
   ls -la alembic/versions/
   ```

4. **测试环境验证**
   ```bash
   # 在测试环境先执行一遍
   ```

5. **执行更新**
   ```bash
   docker-compose build
   docker-compose down
   docker-compose up -d
   ```

6. **验证**
   ```bash
   # 检查日志
   docker-compose logs -f
   
   # 测试 API
   curl http://localhost:8000/health
   ```

7. **回滚准备**
   ```bash
   # 如果出问题,使用备份恢复
   docker-compose down
   cp ./data/backup_before_update.db ./data/llm_orchestrator.db
   docker-compose up -d
   ```

## 总结

### ✅ Docker 重新部署时会自动执行迁移

**关键点**:
1. **数据持久化**: 数据库挂载到宿主机 `./data` 目录
2. **自动迁移**: 容器启动时自动运行 `alembic upgrade head`
3. **智能更新**: Alembic 只执行未应用的新迁移
4. **数据安全**: 迁移前自动备份,支持回滚

**流程**:
```
容器启动 → 检查迁移版本 → 执行新迁移 → 启动应用
```

**无需手动操作**:
- ❌ 不需要手动运行迁移脚本
- ❌ 不需要手动执行 SQL
- ❌ 不需要停止服务单独迁移

**只需确保**:
- ✅ 数据库目录正确挂载
- ✅ 代码包含最新的迁移文件
- ✅ docker-compose up 时一切自动完成

这就是为什么您之前遇到 `no such column` 错误 - 旧的部署没有包含 `004` 迁移,而新代码需要这些字段。现在重新部署后,Alembic 会自动应用 `004` 迁移,添加所有缺失的字段。