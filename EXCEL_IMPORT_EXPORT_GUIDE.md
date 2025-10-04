# Excel 批量导入导出功能说明

## 概述

LLM Orchestrator 提供了基于 Excel 的批量配置导入导出功能,采用**三工作表架构**,参考 llmio-master 项目的设计模式。所有配置统一在一个 Excel 文件中管理,包括:

- **Providers** (提供商)
- **Models** (模型配置)  
- **Associations** (模型-提供商关联)

## 工作表结构

### 1. Providers 工作表

存储 LLM API 提供商的配置信息。

| 列名 | 类型 | 必填 | 说明 | 示例 |
|------|------|------|------|------|
| name | 文本 | 是 | 提供商唯一标识名称 | OpenAI-Main |
| type | 文本 | 是 | 提供商类型 | openai, anthropic, gemini |
| api_key | 文本 | 是 | API 密钥 | sk-xxx |
| base_url | 文本 | 否 | API 基础 URL | https://api.openai.com/v1 |
| priority | 整数 | 否 | 优先级 (默认100) | 100 |
| weight | 整数 | 否 | 负载均衡权重 (默认100) | 100 |
| enabled | 布尔 | 否 | 是否启用 (默认true) | true/false |

**示例数据**:
```
OpenAI-Main | openai | sk-xxx | https://api.openai.com/v1 | 100 | 100 | true
Anthropic-Main | anthropic | sk-ant-xxx | https://api.anthropic.com/v1 | 100 | 100 | true
```

### 2. Models 工作表

存储模型的基本配置信息。

| 列名 | 类型 | 必填 | 说明 | 示例 |
|------|------|------|------|------|
| name | 文本 | 是 | 模型唯一标识名称 | gpt-4o |
| remark | 文本 | 否 | 备注/显示名称 | GPT-4 Optimized |
| max_retry | 整数 | 否 | 最大重试次数 (默认3) | 3 |
| timeout | 整数 | 否 | 超时时间/秒 (默认60) | 60 |

**示例数据**:
```
gpt-4o | GPT-4 Optimized | 3 | 60
claude-3.5-sonnet | Claude 3.5 Sonnet | 3 | 60
```

### 3. Associations 工作表

存储模型与提供商的关联关系和能力配置。

| 列名 | 类型 | 必填 | 说明 | 示例 |
|------|------|------|------|------|
| model_name | 文本 | 是 | 模型名称(必须在Models表中存在) | gpt-4o |
| provider_name | 文本 | 是 | 提供商名称(必须在Providers表中存在) | OpenAI-Main |
| provider_model | 文本 | 是 | 提供商的实际模型名 | gpt-4o-2024-05-13 |
| supports_tools | 布尔 | 否 | 是否支持工具调用 (默认false) | true/false |
| supports_vision | 布尔 | 否 | 是否支持视觉输入 (默认false) | true/false |
| weight | 整数 | 否 | 该关联的权重 (默认100) | 100 |
| enabled | 布尔 | 否 | 是否启用 (默认true) | true/false |

**示例数据**:
```
gpt-4o | OpenAI-Main | gpt-4o-2024-05-13 | true | true | 100 | true
claude-3.5-sonnet | Anthropic-Main | claude-3-5-sonnet-20241022 | true | true | 100 | true
```

## API 端点

### 1. 下载模板

下载 Excel 导入模板,可选择是否包含示例数据。

**请求**:
```
GET /api/admin/export/template?with_sample=true
Authorization: Bearer YOUR_ADMIN_KEY
```

**参数**:
- `with_sample`: 布尔值,是否包含示例数据 (默认: false)

**响应**:
- Excel 文件下载
- 文件名: `llm_orchestrator_template_with_sample.xlsx` 或 `llm_orchestrator_template_empty.xlsx`

### 2. 导出当前配置

导出系统中所有提供商、模型和关联配置到 Excel。

**请求**:
```
GET /api/admin/export/config
Authorization: Bearer YOUR_ADMIN_KEY
```

**响应**:
- Excel 文件下载
- 文件名: `llm_orchestrator_config_20250104_153000.xlsx`
- 包含当前系统中的所有配置数据

### 3. 导入配置

从 Excel 文件批量导入配置。

**请求**:
```
POST /api/admin/import/config/upload
Authorization: Bearer YOUR_ADMIN_KEY
Content-Type: multipart/form-data

file: [Excel文件]
```

**响应**:
```json
{
  "message": "Configuration imported successfully",
  "filename": "config.xlsx",
  "result": {
    "providers": {
      "total": 2,
      "imported": 1,
      "skipped": 1,
      "errors": []
    },
    "models": {
      "total": 2,
      "imported": 2,
      "skipped": 0,
      "errors": []
    },
    "associations": {
      "total": 2,
      "imported": 2,
      "skipped": 0,
      "errors": []
    },
    "summary": {
      "total_imported": 5,
      "total_skipped": 1,
      "total_errors": 0
    }
  }
}
```

## 导入规则

### 去重逻辑

1. **Providers**: 按 `name` 去重
   - 如果提供商名称已存在,跳过该行
   - 记录到 `skipped` 计数

2. **Models**: 按 `name` 去重
   - 如果模型名称已存在,跳过该行
   - 记录到 `skipped` 计数

3. **Associations**: 按 `(model_name, provider_name, provider_model)` 组合去重
   - 如果相同组合已存在,跳过该行
   - 记录到 `skipped` 计数

### 错误处理

导入过程中的错误会被收集并在响应中返回,包括:

- **验证错误**: 必填字段缺失、数据格式错误
- **引用错误**: Associations 中引用的 model_name 或 provider_name 不存在
- **数据库错误**: 数据库操作失败

每个错误包含:
- `row`: 出错的行号 (Excel 中的行号)
- `field`: 出错的字段名
- `error`: 错误详细信息

### 导入顺序

系统按以下顺序处理导入:

1. **Providers** → 创建提供商,建立名称到ID的映射
2. **Models** → 创建模型,建立名称到ID的映射
3. **Associations** → 使用映射表创建关联关系

这确保了关联表引用的提供商和模型都已存在。

## 使用场景

### 场景1: 初始化配置

1. 下载带示例数据的模板:
   ```
   GET /api/admin/export/template?with_sample=true
   ```

2. 根据示例编辑配置

3. 上传导入:
   ```
   POST /api/admin/import/config/upload
   ```

### 场景2: 备份和恢复

**备份配置**:
```
GET /api/admin/export/config
```

**恢复配置**:
```
POST /api/admin/import/config/upload
(上传之前导出的 Excel 文件)
```

### 场景3: 批量更新

1. 导出当前配置
2. 在 Excel 中批量修改
3. 重新导入 (相同名称的记录会被跳过)
4. 如需覆盖,先手动删除旧记录

### 场景4: 环境迁移

在开发/测试/生产环境间迁移配置:

1. 从源环境导出配置
2. 在目标环境导入配置
3. 检查导入结果,处理冲突

## 注意事项

### 1. API 密钥安全

- 导出的 Excel 文件包含明文 API 密钥
- **务必妥善保管导出的文件**
- 不要将配置文件提交到版本控制系统

### 2. 数据一致性

- 导入前建议备份当前配置
- 导入操作不可逆,建议先在测试环境验证
- 检查导入结果中的 errors 字段

### 3. 大批量导入

- 单次导入建议不超过 1000 条记录
- 超大文件可能导致超时,建议分批导入

### 4. 布尔值格式

在 Excel 中,布尔值字段支持以下格式:
- 表示 `true`: `true`, `True`, `TRUE`, `1`, `yes`
- 表示 `false`: `false`, `False`, `FALSE`, `0`, `no`, 空白

### 5. 字符编码

- Excel 文件必须使用 UTF-8 编码
- 建议使用现代 Excel 版本 (2016+)
- 或使用 LibreOffice/WPS 等兼容工具

## 技术实现

### 依赖库

- **openpyxl**: Excel 文件读写
- **SQLAlchemy**: 数据库操作
- **FastAPI**: API 框架

### 性能优化

1. **批量插入**: 使用数据库事务批量提交
2. **内存优化**: 流式处理大文件
3. **索引优化**: 利用数据库索引加速查询

### 错误恢复

- 所有导入操作在事务中执行
- 任何错误发生时自动回滚
- 部分成功的导入会在响应中详细说明

## 与 llmio-master 的差异

### 相似之处

- ✅ 三工作表架构 (Providers, Models, Associations)
- ✅ 统一的 Excel 文件格式
- ✅ 支持批量导入导出
- ✅ 详细的错误报告

### 差异之处

| 特性 | llmio-master | LLM Orchestrator |
|------|-------------|------------------|
| 实现语言 | Go | Python |
| Excel 库 | excelize | openpyxl |
| 模型字段 | 更复杂 (tool_call, structured_output等) | 简化 (仅核心字段) |
| 提供商配置 | JSON 字符串 | 独立字段 |
| 健康检查 | 集成在导入中 | 独立功能模块 |

## 故障排查

### 问题1: 导入失败 - 文件格式错误

**症状**: HTTP 400 错误,提示 "Only .xlsx files are supported"

**解决方案**:
- 确认文件扩展名为 `.xlsx`
- 不要使用 `.xls` (旧版 Excel 格式)
- 重新下载模板并填写数据

### 问题2: 导入部分失败

**症状**: 返回结果中 `errors` 不为空

**解决方案**:
1. 查看 errors 数组中的详细信息
2. 根据 row 和 field 定位问题行
3. 修正后重新导入

### 问题3: 关联创建失败

**症状**: Associations 表导入错误 "Model/Provider not found"

**解决方案**:
- 确认 Providers 和 Models 表数据正确
- 检查 model_name 和 provider_name 拼写
- 确保这些名称在相应的表中存在

## 最佳实践

1. **定期备份**: 每次重要修改前导出当前配置
2. **测试验证**: 在测试环境先验证导入
3. **增量更新**: 使用导入的去重功能增量添加配置
4. **文档同步**: 在 Excel 中添加注释说明配置用途
5. **版本管理**: 为导出的配置文件添加版本号和日期

## 更新日志

### v1.0.0 (2025-01-04)
- ✨ 实现三工作表架构
- ✨ 支持批量导入导出
- ✨ 参考 llmio-master 设计模式
- ✨ 添加详细的错误处理和报告
- ✨ 支持去重和增量导入