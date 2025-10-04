# Token 统计修复指南

## 问题描述

用户报告 Token 使用统计始终显示为 0,即使发送了多个请求后,统计数据仍未更新。

## 根本原因分析

通过深入分析参考项目 llmio-master 和 OrchestrationApi-main,发现当前项目在流式响应 Token 提取逻辑上存在严重缺陷。

### 问题 1: 提取时机错误

**错误实现** (修复前):
```python
async for chunk in provider_instance.chat_completion_stream(request):
    # 在循环中逐个 chunk 解析
    if chunk.startswith("data: "):
        data = json.loads(data_str)
        if "usage" in data:
            usage_info = data["usage"]  # 可能在最终 usage chunk 前退出
    yield chunk
```

问题:
- 在 async for 循环中尝试提取 usage
- 可能在最终包含 usage 的 chunk 到达前就结束循环
- 没有保证获取到最后一个 chunk

### 问题 2: 缺少完整性验证

- 没有保存 last_chunk 确保获取最后的 usage 信息
- 没有验证 total_tokens > 0 来确认数据有效性
- 缺少调试日志,无法追踪 usage 提取过程

## 参考项目实现分析

### llmio-master 的核心机制

TeeReader 并发处理 (chat.go:217-223):
- 使用 io.Pipe + io.TeeReader 创建双向流
- 响应流同时转发给客户端和后台 goroutine
- 后台 goroutine 解析 Token 并更新数据库

Token 提取策略 (tee.go:63-69):
- 保存 lastchunk 变量持续追踪最后一个 chunk
- 流式结束后从 lastchunk 中提取 usage
- 验证 total_tokens != 0 确认有效性

### OrchestrationApi-main 的实现方式

- 透明 HTTP 代理模式
- 请求时传递 StreamOptions 参数
- 日志记录时接收 Token 参数并写入数据库
- 统计查询按日期分组聚合 Token 数据

## 修复方案

### 修复流式响应 Token 提取逻辑

修改文件: app/services/router.py:264-296

修复后代码:
```python
# 追踪最后一个有效 chunk
last_chunk: Optional[str] = None

async for chunk in provider_instance.chat_completion_stream(request):
    # 持续更新 last_chunk (排除 [DONE])
    if chunk.startswith("data: ") and not chunk.startswith("data: [DONE]"):
        last_chunk = chunk
    
    yield chunk

# 流式结束后,从最后一个 chunk 提取 usage
if last_chunk:
    try:
        data_str = last_chunk[6:].strip()
        data = json.loads(data_str)
        
        if "usage" in data:
            usage = data["usage"]
            if usage.get("total_tokens", 0) > 0:
                usage_info = usage
                logger.debug("Extracted usage from last chunk")
    except (json.JSONDecodeError, KeyError) as e:
        logger.warning(f"Failed to extract usage: {str(e)}")
```

关键改进:
1. 保存最后一个 chunk: 使用 last_chunk 变量持续追踪
2. 流式结束后提取: 在 async for 循环结束后统一处理
3. 验证有效性: 检查 total_tokens > 0
4. 调试日志: 添加详细的 usage 提取日志

### 确保 Provider 请求 usage

已实现 (app/providers/openai.py:117):
```python
payload = {
    "model": resolved_model,
    "messages": [...],
    "stream": True,
    "stream_options": {"include_usage": True}
}
```

### 数据库查询优化

已实现 (app/api/routes/admin.py:583-584):
```python
total_tokens = func.coalesce(func.sum(RequestLog.total_tokens), 0)
```

## 测试验证

### 测试工具

1. test_streaming_token_fix.sh - 端到端验证脚本
2. diagnose_token_stats.py - 数据库诊断脚本

### 运行测试

```bash
# 启动应用
uvicorn app.main:app --reload

# 运行验证脚本
bash test_streaming_token_fix.sh

# 运行诊断
python diagnose_token_stats.py
```

### 预期结果

成功标志:
- 日志记录中 total_tokens 非零
- 统计 API 返回累计 Token 总数
- 调试日志显示 "Extracted usage from last chunk"

## 故障排查清单

如果 Token 统计仍为 0:

- 检查 Provider 是否支持返回 usage
- 验证 stream_options 是否生效
- 查看应用日志是否有 "Extracted usage" 记录
- 运行 diagnose_token_stats.py 检查数据库
- 检查最近日志的 total_tokens 字段
- 尝试使用官方 OpenAI API 测试
- 清空历史日志,发送新请求观察
- 检查网络连接,确保最后 chunk 到达

## 技术要点总结

### Python vs Go 实现差异

- llmio-master (Go): goroutine + channel + io.TeeReader
- llm-orchestrator-py (Python): async/await + async generator
- 关键相同点: 都是从最后一个 chunk 提取 usage

### 最佳实践

1. 流式响应处理:
   - 始终追踪 last_chunk
   - 在流式结束后统一提取 usage
   - 验证数据有效性

2. 调试策略:
   - 添加详细的 usage 提取日志
   - 记录 chunk 数量和最后 chunk 内容
   - 使用诊断脚本分析数据库状态

3. 兼容性考虑:
   - 并非所有 Provider 都支持 stream_options
   - 第三方 API 可能有不同的 usage 格式
   - 需要针对不同 Provider 适配

## 参考资源

- llmio-master: service/tee.go, service/chat.go
- OrchestrationApi-main: Services/Core/IRequestLogger.cs
- OpenAI API 文档: Stream Options, Usage Tracking

## 更新日志

- 2025-10-04: 初始版本,完成流式 Token 提取修复