# 模型-提供商映射架构重构总结

## 重构概述

本次重构参考 llmio-master 项目的优秀设计,将模型配置系统从复杂的单体架构改为简洁的模型-提供商映射架构。

## 核心变更

### 1. 数据库模型简化

#### ModelConfig 表变更
**移除字段**:
- `display_name` - 显示名称
- `description` - 描述
- `context_length` - 上下文长度
- `max_output_tokens` - 最大输出 tokens
- `input_price_per_million` - 输入价格
- `output_price_per_million` - 输出价格
- `supports_streaming` - 支持流式
- `supports_functions` - 支持函数调用
- `supports_vision` - 支持视觉
- `metadata` - 元数据

**保留字段**:
- `id` - 主键
- `name` - 模型名称(用户请求时使用)
- `remark` - 备注信息
- `max_retry` - 最大重试次数
- `timeout` - 超时时间(秒)
- `enabled` - 是否启用
- `created_at` - 创建时间
- `updated_at` - 更新时间

#### ModelProvider 表(新增关联表)
这是核心的映射表,连接模型和提供商:
- `id` - 主键
- `model_id` - 模型 ID
- `provider_id` - 提供商 ID
- `provider_model` - 提供商的模型名称
- `weight` - 权重(负载均衡)
- `tool_call` - 是否支持工具调用
- `structured_output` - 是否支持结构化输出
- `image` - 是否支持视觉输入
- `enabled` - 是否启用

### 2. API 端点变更

#### 新增端点
- `GET /admin/model-providers` - 列出模型-提供商关联
  - 可选过滤: `model_id`, `provider_id`
  - 返回包含模型名、提供商名、类型等详细信息

- `POST /admin/model-providers` - 创建模型-提供商关联
  - 自动验证模型和提供商存在性
  - 防止重复关联

- `PATCH /admin/model-providers/{id}` - 更新关联配置
  - 可更新权重、功能支持等

- `DELETE /admin/model-providers/{id}` - 删除关联

- `GET /admin/model-providers/{id}/status` - 获取关联状态历史
  - 返回最近 N 次请求的成功/失败状态
  - 用于可视化健康状态

#### 简化端点
- `POST /admin/models` - 创建模型配置
  - 仅需 `name`, `remark`, `max_retry`, `timeout`, `enabled`
  - 大幅简化表单字段

### 3. Web 界面更新

#### 新增页面
- `model-providers.html` - 模型-提供商关联管理页面
  - 类似 llmio-master 的设计
  - 支持按模型、提供商类型筛选
  - 显示每个关联的状态历史(柱状图)
  - 直观展示哪个提供商的哪个模型有问题

#### 主界面修改
- 添加"模型-提供商关联"导航标签
- 简化模型配置表单
  - 移除上下文长度、价格等复杂字段
  - 仅保留基础配置项

### 4. 数据库迁移

创建迁移脚本 `002_simplify_model_config.py`:
- 自动移除旧字段
- 支持回滚操作
- 兼容已有数据

## 优势对比

### 旧架构问题
1. **配置复杂**: 模型配置包含大量技术细节字段
2. **不够直观**: 无法清楚看到模型与提供商的映射关系
3. **难以诊断**: 多提供商场景下无法确定具体问题源
4. **维护困难**: 模型配置变更影响所有提供商

### 新架构优势
1. **简洁明了**: 模型配置仅包含基础信息
2. **灵活映射**: 一个模型可关联多个提供商
3. **健康可视**: 每个关联独立显示状态历史
4. **易于维护**: 模型与提供商解耦,独立管理

## 使用示例

### 创建模型配置
```python
# 旧方式 - 复杂
{
    "name": "gpt-4",
    "display_name": "GPT-4",
    "context_length": 8192,
    "max_output_tokens": 4096,
    "input_price_per_million": 30.0,
    "output_price_per_million": 60.0,
    "supports_streaming": true,
    "supports_functions": true,
    "supports_vision": false
}

# 新方式 - 简洁
{
    "name": "gpt-4",
    "remark": "OpenAI GPT-4 模型",
    "max_retry": 3,
    "timeout": 30,
    "enabled": true
}
```

### 创建模型-提供商关联
```python
{
    "model_id": 1,           # gpt-4
    "provider_id": 1,        # OpenAI Official
    "provider_model": "gpt-4-0125-preview",
    "weight": 100,
    "tool_call": true,
    "structured_output": true,
    "image": false,
    "enabled": true
}
```

## 部署步骤

### 1. 运行数据库迁移
```bash
cd llm-orchestrator-py
alembic upgrade head
```

### 2. 重新构建 Docker 镜像
```bash
docker build -t ghcr.io/rsv51/llm-orchestrator-py:latest .
docker push ghcr.io/rsv51/llm-orchestrator-py:latest
```

### 3. 重启服务
```bash
# Kubernetes
kubectl delete pod llm-orchestrator-py-0 -n ns-civhcweo

# Docker Compose
docker-compose down
docker-compose up -d
```

### 4. 访问新界面
- 主界面: `https://your-domain.com/admin-ui/`
- 模型-提供商关联: `https://your-domain.com/admin-ui/model-providers.html`

## 迁移建议

### 对于现有数据
1. 备份数据库
2. 运行迁移脚本
3. 为现有模型创建提供商关联
4. 验证功能正常后删除旧配置

### 对于新部署
直接使用新架构,按以下顺序配置:
1. 添加提供商
2. 创建模型配置
3. 建立模型-提供商关联
4. 测试验证

## 技术要点

### 状态历史查询
```python
# 获取最近 10 次请求状态
query = (
    select(RequestLog.status_code, RequestLog.created_at)
    .where(
        and_(
            RequestLog.provider_id == provider_id,
            RequestLog.model == model_name
        )
    )
    .order_by(RequestLog.created_at.desc())
    .limit(10)
)

# 转换为布尔数组(成功/失败)
status_array = [log.status_code == 200 for log in reversed(logs)]
```

### 前端状态可视化
```javascript
// 渲染状态柱状图(类似 llmio-master)
function renderStatusBars(statusHistory) {
    return statusHistory.map(isSuccess => 
        `<div class="status-bar ${isSuccess ? 'success' : 'failure'}" 
              title="${isSuccess ? '成功' : '失败'}"></div>`
    ).join('');
}
```

## 文件清单

### 修改的文件
- `app/models/provider.py` - 简化模型配置
- `app/api/schemas.py` - 更新 Pydantic 模式
- `app/api/routes/admin.py` - 添加关联管理 API
- `web/index.html` - 简化模型表单
- `web/app.js` - 更新前端逻辑

### 新增的文件
- `alembic/versions/002_simplify_model_config.py` - 数据库迁移
- `web/model-providers.html` - 关联管理界面
- `web/model-providers.js` - 关联管理逻辑
- `MODEL_PROVIDER_REFACTOR.md` - 本文档

## 总结

本次重构参考 llmio-master 的优秀设计,成功简化了模型配置系统,提升了可维护性和可观测性。新架构更加直观,便于诊断问题,符合生产环境的实际需求。