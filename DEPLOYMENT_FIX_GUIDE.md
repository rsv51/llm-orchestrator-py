# 数据库迁移错误修复部署指南

## 问题总结

部署失败的原因有两个:

1. **SQL 语法错误**: `admin.py:542` 的 `func.case()` 缺少 `else_` 参数
2. **迁移文件引用错误**: `002_simplify_model_config.py` 的 `down_revision` 引用不正确

## 已修复的文件

### 1. app/api/routes/admin.py (Line 542)
```python
# 修复前
func.sum(func.case((RequestLog.status_code == 200, 1))).label("success")

# 修复后  
func.sum(func.case((RequestLog.status_code == 200, 1), else_=0)).label("success")
```

### 2. alembic/versions/002_simplify_model_config.py (Line 16)
```python
# 修复前
down_revision: Union[str, None] = '001_initial_schema'

# 修复后
down_revision: Union[str, None] = '001'
```

## 部署步骤

### 方案 A: 使用 GitHub Actions (推荐)

1. **推送代码到 GitHub**:
   ```bash
   cd llm-orchestrator-py
   git push origin main
   ```

2. **等待 GitHub Actions 自动构建**:
   - 访问 https://github.com/rsv51/llm-orchestrator-py/actions
   - 等待镜像构建完成
   - 自动推送到 ghcr.io/rsv51/llm-orchestrator-py:latest

3. **重启 K8s Pod**:
   ```bash
   kubectl delete pod llm-orchestrator-py-0 -n ns-civhcweo
   kubectl wait --for=condition=ready pod/llm-orchestrator-py-0 -n ns-civhcweo --timeout=300s
   ```

4. **查看日志验证**:
   ```bash
   kubectl logs -f llm-orchestrator-py-0 -n ns-civhcweo
   ```

### 方案 B: 在有 Docker 的机器上构建

1. **克隆代码** (在有 Docker 的机器上):
   ```bash
   git clone https://github.com/rsv51/llm-orchestrator-py.git
   cd llm-orchestrator-py
   ```

2. **构建并推送镜像**:
   ```bash
   docker build -t ghcr.io/rsv51/llm-orchestrator-py:latest .
   docker login ghcr.io -u rsv51
   docker push ghcr.io/rsv51/llm-orchestrator-py:latest
   ```

3. **重启 K8s Pod**:
   ```bash
   kubectl delete pod llm-orchestrator-py-0 -n ns-civhcweo
   ```

### 方案 C: 手动热修复 (临时方案,不推荐)

如果无法重新部署,可以直接在 Pod 内修改文件:

1. **进入 Pod**:
   ```bash
   kubectl exec -it llm-orchestrator-py-0 -n ns-civhcweo -- /bin/bash
   ```

2. **修改 admin.py**:
   ```bash
   sed -i 's/func\.sum(func\.case((RequestLog\.status_code == 200, 1)))/func.sum(func.case((RequestLog.status_code == 200, 1), else_=0))/' /app/app/api/routes/admin.py
   ```

3. **修改迁移文件**:
   ```bash
   sed -i "s/down_revision: Union\[str, None\] = '001_initial_schema'/down_revision: Union[str, None] = '001'/" /app/alembic/versions/002_simplify_model_config.py
   ```

4. **重启应用** (在 Pod 内):
   ```bash
   pkill -9 uvicorn
   exit
   ```

5. **等待 Pod 自动重启**:
   ```bash
   kubectl wait --for=condition=ready pod/llm-orchestrator-py-0 -n ns-civhcweo --timeout=300s
   ```

**注意**: 方案 C 的修改在 Pod 重启后会丢失,仅用于紧急验证。

## 验证修复

### 1. 检查数据库迁移是否成功
```bash
kubectl logs llm-orchestrator-py-0 -n ns-civhcweo | grep -A 5 "Running database migrations"
```

预期输出应包含:
```
📦 Running database migrations...
INFO  [alembic.runtime.migration] Context impl SQLiteImpl.
INFO  [alembic.runtime.migration] Will assume non-transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> 001, Initial database schema
INFO  [alembic.runtime.migration] Running upgrade 001 -> 002_simplify_model_config, Simplify model config schema
```

### 2. 检查应用是否正常启动
```bash
kubectl logs llm-orchestrator-py-0 -n ns-civhcweo | tail -10
```

预期输出应包含:
```
✅ LLM Orchestrator started successfully!
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### 3. 测试 Web 管理界面

访问 https://xcoixknrypmu.us-west-1.clawcloudrun.com 并登录,检查:
- [ ] 统计数据页面正常加载 (不再报 SQL 语法错误)
- [ ] 模型列表显示简化后的字段 (仅 5 个基础字段)
- [ ] 模型-提供商关联页面可访问

### 4. 测试 API 端点

```bash
# 设置 Admin Key
ADMIN_KEY="your-admin-key"
BASE_URL="https://xcoixknrypmu.us-west-1.clawcloudrun.com"

# 测试统计 API
curl -H "X-Admin-Key: $ADMIN_KEY" "$BASE_URL/admin/stats?hours=24"

# 预期返回 JSON 而不是错误
```

## 回滚方案

如果新版本有问题,可以回滚到之前的版本:

```bash
# 回滚到之前的镜像版本 (需要先记录当前版本)
kubectl set image statefulset/llm-orchestrator-py llm-orchestrator-py=ghcr.io/rsv51/llm-orchestrator-py:previous-tag -n ns-civhcweo

# 或者回滚数据库迁移
kubectl exec -it llm-orchestrator-py-0 -n ns-civhcweo -- alembic downgrade 001
```

## 常见问题

### Q1: 迁移提示 "Revision 001_initial_schema is not present"
**A**: 这是因为 002 迁移文件引用了错误的 revision ID。确保已应用上述修复。

### Q2: Web 界面仍然显示 SQL 错误
**A**: 检查 Pod 是否已经重启并加载了新代码:
```bash
kubectl get pod llm-orchestrator-py-0 -n ns-civhcweo -o jsonpath='{.status.startTime}'
```

### Q3: 数据库迁移卡住
**A**: 检查数据库文件权限:
```bash
kubectl exec -it llm-orchestrator-py-0 -n ns-civhcweo -- ls -la /app/data/
```

## 技术细节

### 为什么需要 else_ 参数?

SQLite 的 CASE 语句语法要求:
```sql
-- 错误 (SQLite 不接受)
SELECT SUM(CASE WHEN status = 200 THEN 1 END)

-- 正确 (必须有 ELSE)
SELECT SUM(CASE WHEN status = 200 THEN 1 ELSE 0 END)
```

SQLAlchemy 通过 `else_` 参数提供 ELSE 分支:
```python
# Python 代码
func.sum(func.case((condition, value), else_=default))

# 生成的 SQL
SUM(CASE WHEN condition THEN value ELSE default END)
```

### 迁移文件命名规范

Alembic 迁移文件的 `revision` 和 `down_revision` 必须匹配:

```python
# 001_initial_schema.py
revision = '001'
down_revision = None

# 002_simplify_model_config.py  
revision = '002_simplify_model_config'
down_revision = '001'  # 必须引用前一个迁移的 revision
```

文件名可以任意,但 `revision` 和 `down_revision` 的值必须精确匹配。

## 联系支持

如果遇到其他问题,请提供以下信息:
1. Pod 完整日志: `kubectl logs llm-orchestrator-py-0 -n ns-civhcweo > logs.txt`
2. Pod 描述: `kubectl describe pod llm-orchestrator-py-0 -n ns-civhcweo > pod-info.txt`
3. 数据库状态: `kubectl exec llm-orchestrator-py-0 -n ns-civhcweo -- sqlite3 /app/data/orchestrator.db ".tables"`