# 负载均衡器模型过滤修复

## 问题描述

负载均衡器之前没有检查 Provider 是否真正支持请求的模型,导致:
- `glm-4.6` 模型被路由到不支持它的 `qwen` Provider
- 请求失败,但仍然被记录为"成功"

## 根本原因

`LoadBalancer.select_provider()` 方法只查询启用且健康的 Provider,但没有通过 `model_providers` 表验证 Provider 是否支持请求的模型。

## 修复方案

### 1. 添加模型过滤查询

新增 `_get_healthy_providers_for_model()` 方法:

```python
async def _get_healthy_providers_for_model(self, model_name: str) -> List[Dict]:
    """
    Get list of healthy providers that support the specified model.
    
    Joins:
    - Provider
    - ModelProvider (model-provider associations)
    - ModelConfig (to get model name)
    - ProviderHealth (health status)
    
    Filters:
    - Provider.enabled = True
    - ModelConfig.name = model_name
    - ModelConfig.enabled = True
    - ModelProvider.enabled = True
    - ProviderHealth.is_healthy = True (or None for new providers)
    """
```

### 2. 修改 select_provider() 逻辑

```python
if model:
    providers_data = await self._get_healthy_providers_for_model(model)
else:
    providers_data = await self._get_healthy_providers()
```

### 3. 组合权重计算

Provider 权重 × ModelProvider 权重 = 最终权重

这允许对同一模型的不同 Provider 配置不同的优先级。

## 关键改进

### 修复前
```python
# ❌ 只检查 Provider 状态
query = select(Provider, ProviderHealth).where(Provider.enabled == True)
# 结果: qwen Provider 被选中处理 glm-4.6 → 失败
```

### 修复后
```python
# ✅ 检查模型支持
query = (
    select(Provider, ProviderHealth, ModelProvider)
    .join(ModelProvider, Provider.id == ModelProvider.provider_id)
    .join(ModelConfig, ModelProvider.model_id == ModelConfig.id)
    .where(
        Provider.enabled == True,
        ModelConfig.name == model_name,  # 只返回支持此模型的 Provider
        ModelConfig.enabled == True,
        ModelProvider.enabled == True
    )
)
# 结果: 只有真正支持 glm-4.6 的 Provider 会被选中
```

## 验证方法

1. 在模型管理页面检查每个模型关联的 Provider
2. 发送请求时检查日志:
   ```
   Found N healthy providers for model glm-4.6
   providers: [5202030, ...]  # 只包含支持该模型的 Provider
   ```
3. 确认不再有"Provider 不支持模型"的错误

## 内存使用问题

关于 Python 应用占用 100M+ 内存的问题:

**这是正常的**。Python 运行时本身就需要基础内存:
- Python 解释器: ~20-30MB
- FastAPI + Uvicorn: ~20-30MB
- SQLAlchemy ORM: ~20-30MB
- 依赖库 (httpx, pydantic, etc): ~20-30MB
- 数据库连接池: ~10-20MB

**总计**: 90-140MB 是 Python 应用的正常基准内存占用。

### 与其他语言对比

- **Go/C#/JavaScript**: 编译型或 JIT 编译语言,运行时开销小
- **Python**: 解释型语言,运行时开销大,但开发效率高

### 优化建议

如果内存是关键约束:
1. 使用轻量级 Python 发行版 (PyPy)
2. 减少数据库连接池大小
3. 考虑迁移到 Go/Rust (但开发成本高)

**结论**: 100M+ 内存对 Python Web 应用来说是合理的,不需要担心。