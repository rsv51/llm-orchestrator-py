# 数据库迁移指南

本目录包含手动 SQL 迁移脚本和工具,用于非 Alembic 环境。

## 重要说明

### Docker 部署用户

**如果您使用 Docker 部署,请阅读 [Docker 部署指南](../DOCKER_DEPLOYMENT_GUIDE.md)**

Docker 容器会在启动时**自动执行 Alembic 迁移**,无需手动运行本目录的脚本。Alembic 迁移文件位于 [`alembic/versions/`](../alembic/versions/) 目录。

### 本目录适用场景

本目录的脚本适用于以下情况:
- ✅ 直接在宿主机运行应用(非 Docker)
- ✅ 无法使用 Alembic 的环境
- ✅ 需要手动控制迁移时机
- ✅ 从旧版本升级且数据库已存在

### Alembic vs 手动迁移

| 特性 | Alembic (推荐) | 手动脚本 (本目录) |
|------|---------------|------------------|
| **适用环境** | Docker, 现代部署 | 宿主机, 传统部署 |
| **自动化** | 完全自动 | 需手动执行 |
| **版本管理** | 内置版本控制 | 需自行管理 |
| **回滚支持** | 支持 | 不支持 |
| **错误处理** | 完善 | 基本 |
| **团队协作** | 优秀 | 一般 |

## 快速开始

### Windows 用户 (推荐)

双击运行批处理文件:
```bash
run_migration.bat
```

### 所有平台

使用 Python 脚本:
```bash
# 从项目根目录执行
python migrations/run_migration.py
```

## 迁移内容

此迁移为 `provider_health` 表添加以下新列:

| 列名 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `response_time_ms` | REAL | 0.0 | Provider 响应时间(毫秒) |
| `error_message` | TEXT | NULL | 最后一次错误消息 |
| `last_check` | TIMESTAMP | CURRENT_TIMESTAMP | 最后健康检查时间 |
| `consecutive_failures` | INTEGER | 0 | 连续失败次数 |
| `success_rate` | REAL | 100.0 | 成功率(百分比) |

## 迁移脚本说明

### 1. add_health_fields.sql
原始 SQL 迁移脚本,包含所有 ALTER TABLE 语句。

**适用场景**: 全新数据库或使用 SQLite CLI 工具

**使用方法**:
```bash
sqlite3 llm_orchestrator.db < migrations/add_health_fields.sql
```

**注意**: 如果列已存在会报错,不推荐用于已部署的数据库。

### 2. run_migration.py
Python 迁移脚本,带完整错误处理。

**特性**:
- ✅ 检测并跳过已存在的列
- ✅ 更新现有记录的数据映射
- ✅ 创建性能优化索引
- ✅ 验证迁移结果
- ✅ 显示示例数据

**使用方法**:
```bash
# 默认数据库路径
python migrations/run_migration.py

# 自定义数据库路径
python migrations/run_migration.py /path/to/database.db
```

**输出示例**:
```
Running migration on: llm_orchestrator.db
✓ Added column: response_time_ms
✓ Added column: error_message
○ Column already exists: last_check
✓ Added column: consecutive_failures
✓ Added column: success_rate
✓ Updated 5 existing records
✓ Created index: idx_health_last_check

✓ Migration successful! Verified 5 records

Sample data:
  Provider 1: healthy=True, response_time=250.5ms
  Provider 2: healthy=True, response_time=180.3ms
```

### 3. run_migration.bat
Windows 批处理包装器。

**特性**:
- ✅ 自动检查数据库文件
- ✅ 友好的错误提示
- ✅ 执行完成后暂停以查看结果

**使用方法**:
双击文件或命令行执行:
```cmd
migrations\run_migration.bat
```

### 4. verify_migration.py
验证迁移是否成功执行。

**使用方法**:
```bash
python migrations/verify_migration.py
```

**输出示例**:
```
Checking database: llm_orchestrator.db
============================================================
✓ id                      INTEGER
✓ provider_id             INTEGER
✓ is_healthy              BOOLEAN
✓ response_time_ms        REAL
✓ error_message           TEXT
✓ last_check              TIMESTAMP
✓ consecutive_failures    INTEGER
✓ success_rate            REAL
============================================================

✅ Migration complete: All 8 required columns exist

Sample data (3 records):
------------------------------------------------------------
Provider 1: healthy=True, response_time=250.5ms, success_rate=98.5%
Provider 2: healthy=True, response_time=180.3ms, success_rate=99.2%
Provider 3: healthy=False, response_time=0.0ms, success_rate=95.0%
```

## 推荐迁移流程

### 1. 备份数据库
```bash
# Windows
copy llm_orchestrator.db llm_orchestrator.db.backup

# Linux/Mac
cp llm_orchestrator.db llm_orchestrator.db.backup
```

### 2. 执行迁移
```bash
# Windows
migrations\run_migration.bat

# Linux/Mac/Python
python migrations/run_migration.py
```

### 3. 验证结果
```bash
python migrations/verify_migration.py
```

### 4. 测试应用
```bash
# 启动应用
python -m uvicorn app.main:app --reload

# 测试健康检查 API
curl -H "Authorization: Bearer YOUR_ADMIN_KEY" \
  http://localhost:8000/api/admin/health
```

## 常见问题

### Q1: 迁移脚本报错 "duplicate column name"

**原因**: 列已经存在
**解决**: 使用 `run_migration.py`,它会自动跳过已存在的列

### Q2: 如何回滚迁移?

**答**: 使用备份恢复:
```bash
# Windows
copy llm_orchestrator.db.backup llm_orchestrator.db

# Linux/Mac
cp llm_orchestrator.db.backup llm_orchestrator.db
```

或手动删除列(SQLite 需要重建表):
```sql
-- 创建临时表
CREATE TABLE provider_health_backup AS SELECT * FROM provider_health;

-- 删除原表
DROP TABLE provider_health;

-- 重新创建原表(不包含新列)
CREATE TABLE provider_health (...);

-- 恢复数据
INSERT INTO provider_health SELECT ... FROM provider_health_backup;

-- 删除临时表
DROP TABLE provider_health_backup;
```

### Q3: 迁移后应用仍然报错?

**检查列表**:
1. 确认迁移成功: `python migrations/verify_migration.py`
2. 重启应用服务
3. 清除缓存(如果有)
4. 检查应用日志

### Q4: 如何在生产环境执行迁移?

**建议流程**:
1. **停止应用服务**
2. **备份数据库**
3. **执行迁移**
4. **验证结果**
5. **启动应用服务**
6. **监控日志和健康状态**

```bash
# 1. 停止服务
systemctl stop llm-orchestrator

# 2. 备份
cp llm_orchestrator.db llm_orchestrator.db.$(date +%Y%m%d_%H%M%S).backup

# 3. 迁移
python migrations/run_migration.py

# 4. 验证
python migrations/verify_migration.py

# 5. 启动
systemctl start llm-orchestrator

# 6. 监控
journalctl -u llm-orchestrator -f
```

## 技术细节

### 数据映射

迁移脚本会自动映射旧字段到新字段:

```sql
UPDATE provider_health
SET 
    last_check = COALESCE(last_validated_at, CURRENT_TIMESTAMP),
    error_message = last_error,
    consecutive_failures = error_count
WHERE last_check IS NULL OR last_check = '';
```

### 索引优化

创建索引提升查询性能:

```sql
CREATE INDEX IF NOT EXISTS idx_health_last_check 
ON provider_health(last_check);
```

### 向后兼容

旧字段保留,不影响现有功能:
- `error_count` → 映射到 `consecutive_failures`
- `last_error` → 映射到 `error_message`
- `last_validated_at` → 映射到 `last_check`

## Alembic 迁移 (推荐)

如果您的项目使用 Alembic(Docker 部署默认使用),迁移文件在:
```
alembic/versions/
├── 001_initial_schema.py          # 初始表结构
├── 002_add_provider_fields.py     # Provider 字段扩展
├── 003_provider_config_to_fields.py # Provider 配置重构
└── 004_add_provider_health_fields.py # ProviderHealth 缺失字段 (最新)
```

### 执行 Alembic 迁移

```bash
# 自动(Docker): 容器启动时自动执行
docker-compose up -d

# 手动执行所有待应用的迁移
alembic upgrade head

# 查看当前版本
alembic current

# 查看迁移历史
alembic history

# 回滚到上一个版本
alembic downgrade -1
```

## 相关文档

- [Docker 部署指南](../DOCKER_DEPLOYMENT_GUIDE.md) - **Docker 用户必读**
- [健康检查修复指南](../HEALTH_CHECK_FIX_GUIDE.md) - 完整的健康检查系统文档
- [数据库优化指南](../DATABASE_OPTIMIZATION.md) - 数据库性能优化建议

## 支持

如遇问题,请检查:
1. Python 版本 >= 3.8
2. SQLite3 已安装
3. 数据库文件权限正确
4. 应用日志中的详细错误信息