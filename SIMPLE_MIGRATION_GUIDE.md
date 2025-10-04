# 简化的数据库迁移策略

## 当前状态

已删除 `002_simplify_model_config.py` 迁移文件,保留 `001_initial_schema.py` 作为唯一的数据库初始化脚本。

## 为什么这样做?

既然每次部署都是全新的,不需要保留旧数据,那么:
- **不需要复杂的迁移链** - 001 迁移已经创建了简化后的表结构
- **避免迁移冲突** - 单一迁移文件,不会有引用错误
- **部署更快** - 只需运行一次迁移,不需要逐步升级

## 001 迁移文件包含的表结构

### 1. models 表 (简化版)
```sql
CREATE TABLE models (
    id INTEGER PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    remark VARCHAR(255),
    max_retry INTEGER DEFAULT 3,
    timeout INTEGER DEFAULT 30,
    enabled BOOLEAN DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

**关键改变**: 直接创建简化版,没有价格、上下文长度等字段。

### 2. model_providers 表 (新增)
```sql
CREATE TABLE model_providers (
    id INTEGER PRIMARY KEY,
    model_id INTEGER NOT NULL,
    provider_id INTEGER NOT NULL,
    provider_model VARCHAR(100) NOT NULL,
    weight INTEGER DEFAULT 1,
    tool_call BOOLEAN DEFAULT 1,
    structured_output BOOLEAN DEFAULT 1,
    image BOOLEAN DEFAULT 0,
    enabled BOOLEAN DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (model_id) REFERENCES models(id) ON DELETE CASCADE,
    FOREIGN KEY (provider_id) REFERENCES providers(id) ON DELETE CASCADE
);
```

**用途**: 实现模型-提供商多对多关联。

### 3. 其他表
- `providers` - 提供商配置
- `request_logs` - 请求日志
- `provider_health` - 提供商健康状态
- `provider_stats` - 提供商统计数据

## 部署流程

### 1. 首次部署
```bash
# 启动容器后自动执行
alembic upgrade head

# 结果:
# - 运行 001_initial_schema
# - 创建所有表
# - 表结构已经是简化版
```

### 2. 后续部署
如果需要修改表结构,有两个选择:

#### 选项 A: 直接修改 001 文件 (推荐)
```python
# 编辑 alembic/versions/001_initial_schema.py
# 修改 CREATE TABLE 语句

# 部署时删除旧数据库
rm data/orchestrator.db
alembic upgrade head
```

#### 选项 B: 创建新的迁移文件
```bash
# 如果确实需要保留数据
alembic revision -m "add_new_field"

# 编辑新文件
# down_revision = '001'
```

## 与之前版本的差异

| 方面 | 之前 | 现在 |
|------|------|------|
| 迁移文件数量 | 2 个 (001 + 002) | 1 个 (001) |
| models 表字段 | 13 个 | 5 个 |
| 迁移依赖链 | 001 → 002 | 仅 001 |
| 部署复杂度 | 需处理迁移顺序 | 一步到位 |
| 回滚能力 | 可回滚到旧结构 | 不需要回滚 |

## 验证数据库结构

```bash
# 进入 Pod
kubectl exec -it llm-orchestrator-py-0 -n ns-civhcweo -- /bin/bash

# 检查表结构
sqlite3 /app/data/orchestrator.db ".schema models"

# 预期输出 (简化版):
CREATE TABLE models (
    id INTEGER NOT NULL,
    name VARCHAR(100) NOT NULL,
    remark VARCHAR(255),
    max_retry INTEGER DEFAULT 3,
    timeout INTEGER DEFAULT 30,
    enabled BOOLEAN DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE (name)
);
```

## 常见问题

### Q: 如果我需要添加新字段怎么办?
**A**: 两种方式:
1. 修改 001 文件并删除数据库重建 (适合无数据场景)
2. 创建新的迁移文件 `002_add_field.py`

### Q: 为什么不保留 002 迁移?
**A**: 因为:
- 每次都是全新部署,不需要从旧结构迁移到新结构
- 001 文件已经直接创建简化后的表结构
- 减少迁移依赖,避免版本冲突

### Q: 如果未来需要迁移旧数据怎么办?
**A**: 如果真的需要从旧版本迁移数据:
```python
# 创建 002_migrate_from_old.py
def upgrade():
    # 读取旧表数据
    # 转换并插入新表
    pass
```

## 技术说明

### Alembic 版本表
迁移执行后,数据库会有 `alembic_version` 表:

```sql
SELECT * FROM alembic_version;
-- version
-- -------
-- 001
```

只有一个版本号 `001`,表示当前数据库状态。

### 为什么这样更简单?

**之前的复杂流程**:
```
空数据库 → 001(创建复杂表) → 002(删除10个字段) = 简化表
```

**现在的简单流程**:
```
空数据库 → 001(直接创建简化表) = 简化表
```

节省了中间步骤,避免了迁移文件之间的依赖关系。

## 总结

对于每次都是全新部署的场景:
- ✅ 保持单一迁移文件 (001)
- ✅ 直接创建目标表结构
- ✅ 避免迁移链复杂性
- ✅ 部署快速可靠

如果未来真的需要保留数据和迁移历史,再考虑添加新的迁移文件也不迟。