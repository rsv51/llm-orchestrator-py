# 数据库迁移快速参考

## 30 秒了解

### Docker 用户 👉 无需手动操作

```bash
# 重新部署即可,迁移自动完成
docker-compose down && docker-compose build && docker-compose up -d
```

**原理**: 容器启动时自动运行 `alembic upgrade head`

---

### 非 Docker 用户 👉 需要手动迁移

```bash
# 方式 1: Alembic (推荐)
alembic upgrade head

# 方式 2: Python 脚本
python migrations/run_migration.py

# 方式 3: Windows 批处理
migrations\run_migration.bat
```

---

## 核心概念

### 什么是数据库迁移?

数据库迁移 = **代码更新时同步数据库结构**

```
旧代码 + 旧数据库 → 新代码 + 旧数据库 = ❌ 报错
旧代码 + 旧数据库 → 新代码 + 新数据库 = ✅ 正常
                      ↑
                   需要迁移
```

### 为什么 Docker 不需要手动迁移?

**entrypoint 脚本自动化**:

```bash
# scripts/docker-entrypoint.sh
alembic upgrade head  # ← 自动执行
uvicorn app.main:app  # ← 然后启动
```

### 迁移版本管理

```
alembic/versions/
├── 001_initial_schema.py       (已应用)
├── 002_add_provider_fields.py  (已应用)
├── 003_provider_config.py      (已应用)
└── 004_health_fields.py        (← 新增,待应用)
```

Alembic 记住哪些版本已执行,只运行新的。

---

## 常见场景

### 场景 1: 首次部署 Docker

```bash
docker-compose up -d
```

**发生什么**:
1. 创建数据库文件
2. 执行 001 → 002 → 003 → 004
3. 启动应用

**结果**: 全新数据库,所有表和字段齐全 ✅

---

### 场景 2: 更新代码重新部署

```bash
git pull
docker-compose down
docker-compose build
docker-compose up -d
```

**发生什么**:
1. 检测数据库当前版本(例如 003)
2. 只执行新迁移 004
3. 启动应用

**结果**: 数据保留,新字段添加 ✅

---

### 场景 3: 仅重启容器

```bash
docker-compose restart
```

**发生什么**:
1. 检测所有迁移已应用
2. 跳过迁移
3. 直接启动

**结果**: 秒启动 ✅

---

## 数据安全

### ⚠️ 数据持久化必需配置

```yaml
# docker-compose.yml
volumes:
  - ./data:/app/data  # ← 必须有这行
```

**没有这行**: 每次重启数据丢失 ❌  
**有这行**: 数据永久保存 ✅

---

## 验证迁移

### 方法 1: 检查日志

```bash
docker-compose logs | grep migration

# 看到这个说明成功:
# ✅ Running upgrade 003 -> 004
```

### 方法 2: 检查版本

```bash
docker exec -it llm-orchestrator alembic current

# 输出:
# 004 (head)  ← 说明最新
```

### 方法 3: 测试 API

```bash
curl http://localhost:8000/api/admin/health

# 不报错 = 成功 ✅
```

---

## 故障排除

### 问题: 报错 "no such column"

**原因**: 迁移未执行  
**解决**:

```bash
# 手动执行迁移
docker exec -it llm-orchestrator alembic upgrade head

# 然后重启
docker-compose restart
```

---

### 问题: 数据库被锁定

**原因**: 多个进程访问数据库  
**解决**:

```bash
# 停止所有容器
docker-compose down

# 重新启动
docker-compose up -d
```

---

### 问题: 每次重启数据丢失

**原因**: 未挂载数据卷  
**解决**:

```yaml
# 检查 docker-compose.yml
volumes:
  - ./data:/app/data  # ← 确保有这行
```

---

## 迁移文件位置

| 类型 | 位置 | 用途 |
|------|------|------|
| **Alembic** | `alembic/versions/*.py` | Docker 自动使用 |
| **手动 SQL** | `migrations/*.sql` | 非 Docker 手动用 |
| **Python 脚本** | `migrations/*.py` | 非 Docker 手动用 |

---

## 详细文档

- 🐳 [Docker 部署指南](DOCKER_DEPLOYMENT_GUIDE.md) - Docker 用户完整指南
- 🔧 [手动迁移指南](migrations/README.md) - 非 Docker 用户指南
- 🏥 [健康检查修复](HEALTH_CHECK_FIX_GUIDE.md) - 问题诊断和修复

---

## 一句话总结

**Docker 用户**: 重新部署就行,啥都别管 🚀  
**非 Docker 用户**: 执行 `alembic upgrade head` 或手动脚本 🔧