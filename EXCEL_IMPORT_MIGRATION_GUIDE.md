# Excel 导入字段迁移指南

## 问题说明

如果您在导入 Excel 时遇到以下错误:
```
'display_name' is an invalid keyword argument for ModelConfig
```

这是因为您使用的 Excel 文件包含旧版本的字段名。本指南将帮助您更新 Excel 文件格式。

## 字段变更对照表

### Models 工作表字段变更

| 旧字段名 | 新字段名 | 说明 |
|---------|---------|------|
| `display_name` | `remark` | 模型描述/备注信息 |
| `description` | `remark` | 模型描述(合并到 remark) |
| `context_length` | ❌ 已删除 | 不再使用 |
| `input_price` | ❌ 已删除 | 不再使用 |
| `output_price` | ❌ 已删除 | 不再使用 |
| `max_tokens` | ❌ 已删除 | 不再使用 |
| `supports_streaming` | ❌ 已删除 | 不再使用 |
| `supports_functions` | ❌ 已删除 | 功能移至 Associations |

### 当前 Models 工作表标准格式

```
| name              | remark                  | max_retry | timeout |
|-------------------|-------------------------|-----------|---------|
| gpt-4o            | GPT-4 Optimized         | 3         | 60      |
| claude-3.5-sonnet | Claude 3.5 Sonnet       | 3         | 60      |
```

**字段说明**:
- `name` (必填): 模型名称,用户请求时使用的标识符
- `remark` (可选): 模型的描述或备注信息
- `max_retry` (可选,默认3): 失败时的最大重试次数
- `timeout` (可选,默认30): 请求超时时间(秒)

### Associations 工作表字段变更

| 旧字段名 | 新字段名 | 说明 |
|---------|---------|------|
| `supports_tools` | `supports_tools` | ✅ 保持不变,但某些旧文件可能缺少此列 |
| `supports_vision` | `supports_vision` | ✅ 保持不变,但某些旧文件可能缺少此列 |

### 当前 Associations 工作表标准格式

```
| model_name        | provider_name  | provider_model              | supports_tools | supports_vision | weight | enabled |
|-------------------|----------------|----------------------------|----------------|-----------------|--------|---------|
| gpt-4o            | OpenAI-Main    | gpt-4o-2024-05-13          | true           | true            | 100    | true    |
| claude-3.5-sonnet | Anthropic-Main | claude-3-5-sonnet-20241022 | true           | true            | 100    | true    |
```

## 解决方案

### 方案 1: 下载新模板(推荐)

1. 登录管理后台
2. 进入"系统设置" → "Excel 批量管理"
3. 点击"📄 下载空白模板"或"📝 下载带示例模板"
4. 使用新模板重新填写数据

### 方案 2: 手动修改现有文件

如果您有大量数据已经填写在旧版 Excel 中,可以手动修改:

#### 步骤 1: 更新 Models 工作表表头

**打开您的 Excel 文件,找到 "Models" 工作表**

旧表头:
```
name | display_name | description | context_length | max_retry | timeout | ...
```

新表头:
```
name | remark | max_retry | timeout
```

**修改步骤**:
1. 删除 `context_length`、`input_price`、`output_price`、`max_tokens` 等列
2. 将 `display_name` 列名改为 `remark`
3. 如果同时有 `description`,将其内容合并到 `remark` 列,然后删除 `description` 列
4. 确保只保留: `name`、`remark`、`max_retry`、`timeout`

#### 步骤 2: 更新 Associations 工作表表头

**找到 "Associations" 工作表**

确保表头包含以下列(按顺序):
```
model_name | provider_name | provider_model | supports_tools | supports_vision | weight | enabled
```

如果缺少 `supports_tools` 或 `supports_vision` 列:
1. 在第 4 列插入 `supports_tools`,默认值填 `true`
2. 在第 5 列插入 `supports_vision`,根据模型实际支持情况填写

### 方案 3: 使用 Excel 公式快速转换

如果您的 Models 工作表有 `display_name` 和 `description`:

1. 在新的 `remark` 列使用公式合并:
   ```excel
   =IF(ISBLANK(B2), C2, IF(ISBLANK(C2), B2, B2 & " - " & C2))
   ```
   其中 B2 是 display_name,C2 是 description

2. 复制公式结果
3. 选择性粘贴为"值"
4. 删除原有的 `display_name` 和 `description` 列

## 导入验证清单

在导入之前,请确认您的 Excel 文件:

### Providers 工作表
- ✅ 表头: `name`, `type`, `api_key`, `base_url`, `priority`, `weight`, `enabled`
- ✅ 每行的 `name` 唯一
- ✅ `type` 只能是: `openai`, `anthropic`, `gemini`
- ✅ `enabled` 只能是: `true` 或 `false`

### Models 工作表
- ✅ 表头: `name`, `remark`, `max_retry`, `timeout`
- ✅ 每行的 `name` 唯一
- ✅ **没有** `display_name`、`description`、`context_length` 等旧字段
- ✅ `max_retry` 是数字(可选,默认3)
- ✅ `timeout` 是数字(可选,默认30)

### Associations 工作表
- ✅ 表头: `model_name`, `provider_name`, `provider_model`, `supports_tools`, `supports_vision`, `weight`, `enabled`
- ✅ `model_name` 必须在 Models 工作表中存在
- ✅ `provider_name` 必须在 Providers 工作表中存在
- ✅ 布尔值(`supports_tools`, `supports_vision`, `enabled`)只能是 `true` 或 `false`
- ✅ `weight` 是数字

## 常见错误和解决方法

### 错误 1: `'display_name' is an invalid keyword argument`
**原因**: Models 工作表使用了旧字段名 `display_name`  
**解决**: 将列名改为 `remark`

### 错误 2: `Model 'xxx' not found`
**原因**: Associations 中引用的 `model_name` 在 Models 工作表中不存在  
**解决**: 
1. 确保 Models 工作表中先导入了该模型
2. 检查模型名称拼写是否完全一致(区分大小写)

### 错误 3: `Provider 'xxx' not found`
**原因**: Associations 中引用的 `provider_name` 在 Providers 工作表中不存在  
**解决**:
1. 确保 Providers 工作表中先导入了该提供商
2. 检查提供商名称拼写是否完全一致(区分大小写)

### 错误 4: 导入时显示 `undefined 个`
**原因**: 前端显示问题,实际数据可能已成功导入  
**解决**: 刷新页面查看实际导入结果,或查看错误详情

## 推荐工作流程

为了避免错误,建议按以下顺序导入:

1. **先导入 Providers**
   - 确保所有提供商配置正确
   - 记录每个 Provider 的 `name`

2. **再导入 Models**
   - 使用新的字段格式(`remark` 而非 `display_name`)
   - 记录每个 Model 的 `name`

3. **最后导入 Associations**
   - 使用前两步记录的 `provider_name` 和 `model_name`
   - 确保名称完全匹配

## 标准模板示例

### 完整的 Excel 文件示例

**Sheet 1: Providers**
```
name           | type      | api_key      | base_url                        | priority | weight | enabled
OpenAI-Main    | openai    | sk-xxx       | https://api.openai.com/v1       | 100      | 100    | true
Anthropic-Main | anthropic | sk-ant-xxx   | https://api.anthropic.com/v1    | 100      | 100    | true
```

**Sheet 2: Models**
```
name              | remark                  | max_retry | timeout
gpt-4o            | GPT-4 Optimized         | 3         | 60
claude-3.5-sonnet | Claude 3.5 Sonnet       | 3         | 60
```

**Sheet 3: Associations**
```
model_name        | provider_name  | provider_model              | supports_tools | supports_vision | weight | enabled
gpt-4o            | OpenAI-Main    | gpt-4o-2024-05-13          | true           | true            | 100    | true
claude-3.5-sonnet | Anthropic-Main | claude-3-5-sonnet-20241022 | true           | true            | 100    | true
```

## 技术支持

如果您在迁移过程中遇到其他问题:

1. 检查服务器日志获取详细错误信息
2. 使用"下载所有配置"导出当前数据作为参考
3. 参考 [`BUG_FIX_SUMMARY.md`](./BUG_FIX_SUMMARY.md) 了解最新的系统变更

---

**最后更新**: 2025-10-04  
**适用版本**: v1.1.0+