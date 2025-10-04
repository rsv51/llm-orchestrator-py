# 健康检查系统修复指南

## 问题描述

前端显示"系统状态: unhealthy"和"暂无提供商"的原因是 `ProviderHealth` 数据库模型字段与 API 响应 schema 不匹配。

### 症状

1. 前端显示系统状态为 `unhealthy`
2. 提供商健康状态列表为空("暂无提供商")
3. 统计数据正常显示(总请求数、成功率等)
4. API 健康检查端点返回 500 错误或字段缺失错误

## 根本原因

[`app/models/health.py`](llm-orchestrator-py/app/models/health.py:14) 中的 `ProviderHealth` 模型缺少以下字段:
- `response_time_ms` (Float) - 响应时间(毫秒)
- `error_message` (Text) - 错误消息
- `last_check` (DateTime) - 最后检查时间
- `consecutive_failures` (Integer) - 连续失败次数
- `success_rate` (Float) - 成功率

这些字段在 [`app/api/schemas.py`](llm-orchestrator-py/app/api/schemas.py:236) 的 `ProviderHealthStatus` schema 中被要求。

## 解决方案

### 1. 数据库模型修复

已更新 [`app/models/health.py`](llm-orchestrator-py/app/models/health.py:14) 添加必需字段:

```python
class ProviderHealth(Base):
    """Provider health status tracking."""
    
    # 新增字段 (与 API schema 匹配)
    is_healthy = Column(Boolean, default=True, index=True)
    response_time_ms = Column(Float, default=0.0)
    error_message = Column(Text)
    last_check = Column(DateTime, default=datetime.utcnow, index=True)
    consecutive_failures = Column(Integer, default=0)
    success_rate = Column(Float, default=100.0)
    
    # 保留旧字段以向后兼容
    error_count = Column(Integer, default=0)
    last_error = Column(Text)
    last_validated_at = Column(DateTime, default=datetime.utcnow)
    # ...
```

### 2. 数据库迁移

#### Docker 部署 (推荐 - 全自动)

**如果您使用 Docker 部署,无需任何手动操作!**

```bash
# 重新部署容器,自动执行 Alembic 迁移
docker-compose down
docker-compose build
docker-compose up -d

# 容器启动时会自动:
# 1. 检测待应用的迁移
# 2. 执行 Alembic 迁移 004
# 3. 添加所有缺失的字段
# 4. 启动应用
```

查看详细说明: [Docker 部署指南](DOCKER_DEPLOYMENT_GUIDE.md)

#### Alembic 迁移 (标准方式)

**如果您使用 Alembic**:

```bash
# 执行所有待应用的迁移
alembic upgrade head

# 验证当前版本
alembic current
# 应显示: 004 (head)

# 查看迁移历史
alembic history
```

迁移文件: [`alembic/versions/004_add_provider_health_fields.py`](alembic/versions/004_add_provider_health_fields.py)

#### 手动迁移 (备选方案)

**如果不使用 Docker 或 Alembic**:

##### 方式 1: Windows - 双击运行批处理文件
```bash
# 项目根目录下执行
migrations\run_migration.bat
```

##### 方式 2: Python 脚本
```bash
python migrations/run_migration.py llm_orchestrator.db
```

##### 方式 3: SQLite 命令行
```bash
sqlite3 llm_orchestrator.db < migrations/add_health_fields.sql
```

**注意**: 手动迁移脚本包含完整的错误处理,可安全重复执行。

查看详细说明: [手动迁移指南](migrations/README.md)

### 3. 健康检查 API 优化

已更新 [`app/api/routes/admin.py`](llm-orchestrator-py/app/api/routes/admin.py:426) 的 [`get_system_health()`](llm-orchestrator-py/app/api/routes/admin.py:431) 函数:

**关键改进**:
- 自动为所有 Provider 创建 ProviderHealth 记录(如果不存在)
- 使用正确的字段映射返回健康状态
- 确保即使没有健康记录也能正常显示 Provider 列表

```python
# 为所有 Provider 初始化健康记录
for provider in all_providers:
    health_query = select(ProviderHealth).where(ProviderHealth.provider_id == provider.id)
    health_result = await db.execute(health_query)
    health_record = health_result.scalar_one_or_none()
    
    if not health_record:
        health_record = ProviderHealth(
            provider_id=provider.id,
            is_healthy=True,
            response_time_ms=0.0,
            error_message=None,
            last_check=datetime.utcnow(),
            consecutive_failures=0,
            success_rate=100.0
        )
        db.add(health_record)
```

## 验证修复

### 1. 检查数据库表结构

```sql
PRAGMA table_info(provider_health);
-- 应该包含以下列:
-- response_time_ms, error_message, last_check, consecutive_failures, success_rate
```

### 2. 测试健康检查 API

```bash
curl -H "Authorization: Bearer YOUR_ADMIN_KEY" \
  http://localhost:8000/api/admin/health | jq
```

预期响应:
```json
{
  "status": "healthy",
  "timestamp": "2025-10-04T14:15:00Z",
  "providers": [
    {
      "provider_id": 1,
      "provider_name": "OpenAI-Main",
      "is_healthy": true,
      "response_time_ms": 250.5,
      "error_message": null,
      "last_check": "2025-10-04T14:14:00Z",
      "consecutive_failures": 0,
      "success_rate": 98.5
    }
  ],
  "database_status": "healthy",
  "cache_status": "healthy"
}
```

### 3. 检查前端显示

访问管理界面 `http://localhost:8000/admin-ui/`:
- 系统状态应显示为 "healthy" (如果有健康的 Provider)
- 提供商健康状态列表应正确显示所有 Provider
- 每个 Provider 应显示健康指示器和响应时间

## 系统状态判断逻辑

```python
# 在 get_system_health() 中:
if total_providers == 0:
    system_status = "unhealthy"  # 没有 Provider
elif healthy_count == total_providers:
    system_status = "healthy"    # 所有 Provider 健康
elif healthy_count > 0:
    system_status = "degraded"   # 部分 Provider 健康
else:
    system_status = "unhealthy"  # 所有 Provider 不健康
```

## 常见问题

### Q1: 为什么迁移后仍显示 "unhealthy"?

**A**: 检查是否有 Provider 记录:
```sql
SELECT COUNT(*) FROM providers;
```
如果为 0,需要先创建 Provider。系统设计为没有 Provider 时状态为 "unhealthy"。

### Q2: 如何手动创建 Provider 健康记录?

**A**: 通过健康检查 API 会自动创建,或手动插入:
```sql
INSERT INTO provider_health (
    provider_id, is_healthy, response_time_ms, 
    last_check, consecutive_failures, success_rate
) VALUES (
    1, 1, 0.0, 
    CURRENT_TIMESTAMP, 0, 100.0
);
```

### Q3: 旧的健康数据会丢失吗?

**A**: 不会。迁移脚本保留了所有旧字段(`error_count`, `last_error`, `last_validated_at` 等)以实现向后兼容。

### Q4: 如何实时更新健康状态?

**A**: 健康状态通过请求日志自动更新。每次 API 调用后,[`RequestRouter`](llm-orchestrator-py/app/services/router.py:44) 会记录结果到 [`RequestLog`](llm-orchestrator-py/app/models/request_log.py),然后由后台任务更新 `ProviderHealth`。

## 相关文件

- [`app/models/health.py`](llm-orchestrator-py/app/models/health.py) - 健康模型定义
- [`app/api/schemas.py`](llm-orchestrator-py/app/api/schemas.py:236) - API 响应 schema
- [`app/api/routes/admin.py`](llm-orchestrator-py/app/api/routes/admin.py:426) - 健康检查端点
- [`migrations/add_health_fields.sql`](llm-orchestrator-py/migrations/add_health_fields.sql) - 数据库迁移脚本
- [`web/app.js`](llm-orchestrator-py/web/app.js:136) - 前端健康检查逻辑

## 后续优化建议

1. **实时健康监控**: 添加定期健康检查任务(每分钟)
2. **告警机制**: Provider 连续失败 N 次后发送通知
3. **健康历史**: 记录历史健康数据用于趋势分析
4. **自动恢复**: 不健康的 Provider 自动重试并标记恢复

## 总结

这次修复解决了 ProviderHealth 模型与 API schema 不匹配的问题,确保:
- ✅ 健康检查 API 返回正确的数据结构
- ✅ 前端能够正确显示系统和 Provider 健康状态
- ✅ 自动初始化缺失的健康记录
- ✅ 向后兼容旧数据

系统现在能够准确反映 Provider 的真实健康状态,为故障转移和负载均衡提供可靠的数据基础。