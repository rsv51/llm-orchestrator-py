# 容器重启问题修复指南

## 🔍 问题诊断

### 错误症状
```
BackOff, Last Occur: 23h59m
Back-off restarting failed container
```

### 根本原因
容器启动时失败,Kubernetes/Docker 不断尝试重启。主要原因:

1. **缺少 Alembic 配置文件** ❌
   - `alembic.ini` - Alembic 主配置
   - `alembic/env.py` - 数据库连接配置
   - `alembic/script.py.mako` - 迁移模板
   - `alembic/versions/001_initial_schema.py` - 初始数据库架构

2. **迁移依赖错误** ❌
   - `002_add_provider_fields.py` 依赖 `001` 但 `001` 不存在

## ✅ 已完成的修复

### 1. 创建 Alembic 配置文件

#### `alembic.ini`
- Alembic 主配置文件
- 定义迁移脚本位置和日志配置

#### `alembic/env.py`
- 数据库连接环境配置
- 导入所有模型确保正确迁移
- 支持异步数据库操作

#### `alembic/script.py.mako`
- 迁移脚本模板
- 用于生成新迁移文件

### 2. 创建完整迁移链

#### `001_initial_schema.py` (新增)
- 创建所有基础表:
  - `providers` - 提供商配置
  - `models` - 模型配置
  - `model_providers` - 模型-提供商关联
  - `request_logs` - 请求日志
  - `provider_health` - 健康状态
  - `provider_stats` - 统计数据

#### `002_add_provider_fields.py` (已存在)
- 添加 Provider 缺失字段:
  - `priority`, `weight`, `max_retries`, `timeout`, `rate_limit`

### 3. 更新部署配置

所有文件已就位,现在可以正常部署。

## 🚀 部署步骤

### 方式 A: 完全重建(推荐)

```bash
# 进入项目目录
cd llm-orchestrator-py

# 停止并删除所有容器和数据
docker-compose down -v

# 重新构建镜像
docker-compose build

# 启动服务
docker-compose up -d

# 查看启动日志
docker-compose logs -f app
```

### 方式 B: Kubernetes 部署

```bash
# 删除现有 Pod
kubectl delete pod llm-orchestrator-py-0 -n ns-civhcweo

# 如果需要,重新构建镜像
docker build -t your-registry/llm-orchestrator:latest .
docker push your-registry/llm-orchestrator:latest

# 重新部署
kubectl rollout restart statefulset/llm-orchestrator-py -n ns-civhcweo

# 查看 Pod 状态
kubectl get pods -n ns-civhcweo -w

# 查看日志
kubectl logs -f llm-orchestrator-py-0 -n ns-civhcweo
```

## 📋 验证步骤

### 1. 检查容器状态

**Docker Compose:**
```bash
docker-compose ps
```

应该显示:
```
NAME                    STATUS      PORTS
llm-orchestrator-py-app Up         0.0.0.0:8000->8000/tcp
llm-orchestrator-py-db  Up         3306/tcp
llm-orchestrator-py-redis Up       6379/tcp
```

**Kubernetes:**
```bash
kubectl get pods -n ns-civhcweo
```

应该显示:
```
NAME                    READY   STATUS    RESTARTS   AGE
llm-orchestrator-py-0   1/1     Running   0          2m
```

### 2. 查看启动日志

期望看到的日志:
```
🚀 Starting LLM Orchestrator...
⏳ Waiting for database...
✅ Database is ready!
📦 Running database migrations...
INFO [alembic.runtime.migration] Context impl SQLiteImpl.
INFO [alembic.runtime.migration] Will assume non-transactional DDL.
INFO [alembic.runtime.migration] Running upgrade  -> 001, Initial database schema
INFO [alembic.runtime.migration] Running upgrade 001 -> 002, Add priority, weight, max_retries, timeout, rate_limit to Provider
🔧 Initializing database...
✅ Starting application server...
INFO:     Started server process [1]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### 3. 测试 API 端点

```bash
# 健康检查
curl http://your-domain/health

# 预期响应
{"status":"healthy","timestamp":"2025-10-04T06:00:00Z"}

# 获取提供商列表(需要 Admin Key)
curl -H "Authorization: Bearer YOUR_ADMIN_KEY" \
     http://your-domain/admin/providers

# 预期响应
[]  # 空数组表示成功,没有错误
```

### 4. 访问 Web 管理界面

```
http://your-domain/admin-ui/login.html
```

登录后应能看到完整的管理界面。

## 🔍 故障排查

### 问题 1: 容器仍然重启

```bash
# 查看详细日志
docker-compose logs --tail=100 app

# 或 Kubernetes
kubectl logs llm-orchestrator-py-0 -n ns-civhcweo --tail=100
```

**可能原因**:
1. 数据库连接失败
2. 环境变量配置错误
3. 权限问题

**解决方法**:
```bash
# 检查环境变量
docker-compose exec app env | grep DATABASE_URL

# 检查数据库连接
docker-compose exec app python -c "
from app.core.config import get_settings
from sqlalchemy import create_engine
settings = get_settings()
print(f'Database URL: {settings.database_url}')
engine = create_engine(settings.database_url)
conn = engine.connect()
print('Database connection successful!')
"
```

### 问题 2: 迁移失败

```bash
# 手动运行迁移
docker-compose exec app alembic current
docker-compose exec app alembic upgrade head

# 如果失败,查看详细错误
docker-compose exec app alembic upgrade head --verbose
```

**可能原因**:
1. 迁移文件语法错误
2. 数据库表已存在冲突

**解决方法**:
```bash
# 重置数据库(会删除所有数据!)
docker-compose down -v
docker-compose up -d --build
```

### 问题 3: 权限错误

```bash
# 检查文件权限
ls -la llm-orchestrator-py/scripts/docker-entrypoint.sh

# 应该显示 -rwxr-xr-x (可执行)
```

**解决方法**:
```bash
# 添加执行权限
chmod +x llm-orchestrator-py/scripts/docker-entrypoint.sh

# 重新构建
docker-compose build
```

### 问题 4: 数据库未就绪

容器启动但立即退出,日志显示数据库连接超时。

**解决方法**:
```bash
# 增加等待时间
# 编辑 docker-entrypoint.sh 中的:
max_retries = 30  # 改为更大的值,如 60
retry_interval = 2  # 保持或增加

# 或确保数据库容器先启动
docker-compose up -d db
sleep 10
docker-compose up -d app
```

## 📁 完整文件列表

现在项目应该包含:

```
llm-orchestrator-py/
├── alembic.ini                          # ✅ 新增
├── alembic/
│   ├── env.py                          # ✅ 新增
│   ├── script.py.mako                  # ✅ 新增
│   └── versions/
│       ├── 001_initial_schema.py       # ✅ 新增
│       └── 002_add_provider_fields.py  # ✅ 已存在
├── scripts/
│   └── docker-entrypoint.sh            # ✅ 已更新
├── Dockerfile                          # ✅ 已更新
├── docker-compose.yml
└── app/
    ├── models/
    │   └── provider.py                 # ✅ 已更新(添加字段)
    └── ...
```

## 🎯 下一步

1. **重新部署服务**
   ```bash
   docker-compose down -v
   docker-compose up -d --build
   ```

2. **验证启动成功**
   ```bash
   docker-compose logs -f app
   ```

3. **测试管理界面**
   - 访问登录页面
   - 添加第一个提供商
   - 获取模型列表

4. **配置提供商**
   - 添加 OpenAI/Anthropic/Gemini 提供商
   - 设置优先级和权重
   - 导入模型配置

## 📚 相关文档

- [数据库修复指南](DATABASE_FIX_GUIDE.md)
- [快速开始](QUICKSTART.md)
- [架构文档](docs/ARCHITECTURE.md)
- [README](README.md)

## ✨ 预期结果

修复后:
- ✅ 容器正常启动,不再重启
- ✅ 数据库迁移自动运行
- ✅ API 端点正常响应
- ✅ Web 管理界面可访问
- ✅ 提供商管理功能正常
- ✅ 所有新字段可用(priority, weight, etc.)