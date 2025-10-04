# 流式请求日志记录问题 - 紧急修复

## 问题诊断

**现象**:
- ✅ 客户端请求成功,流式响应正常
- ❌ 后台日志显示请求失败或无记录
- ❌ Token 统计始终为 0

**根本原因**:

在 `router.py:224-328` 的 `route_streaming_request` 方法中,日志记录代码位于 `async for` 循环**之后**:

```python
async for chunk in provider_instance.chat_completion_stream(request):
    last_chunk = chunk
    yield chunk  # ← 控制权返回给 StreamingResponse

# ❌ 下面的代码永远不会执行!
if last_chunk:
    # 提取 usage
    usage_info = ...

await self._log_streaming_request(...)  # 永远不会被调用
```

**为什么不会执行**:
1. `route_streaming_request` 是 AsyncGenerator
2. `yield chunk` 将控制权交给 FastAPI 的 `StreamingResponse`
3. StreamingResponse 持续消费 chunks 直到流结束
4. Generator 在最后一个 `yield` 后"暂停",**不会继续执行后面的代码**
5. 日志记录代码从未被执行

## Python AsyncGenerator 的限制

不能直接在 finally 块中使用 yield:

```python
# ❌ 这样会语法错误
async def generator():
    try:
        yield data
    finally:
        # 不能在 finally 中 await 数据库操作
        await log_to_database()  # SyntaxError!
```

## 修复方案

### 方案 1: 使用后台任务(推荐)

修改 `chat.py` 在 StreamingResponse 完成后记录日志:

```python
from fastapi import BackgroundTasks

@router.post("/completions")
async def create_chat_completion(
    request: ChatCompletionRequest,
    background_tasks: BackgroundTasks,
    ...
):
    if request.stream:
        # 创建一个状态追踪对象
        stream_state = {
            "last_chunk": None,
            "error": None
        }
        
        # 包装 generator 追踪状态
        async def tracked_stream():
            try:
                async for chunk in router_service.route_streaming_request(...):
                    if chunk.startswith("data: ") and not chunk.startswith("data: [DONE]"):
                        stream_state["last_chunk"] = chunk
                    yield chunk
            except Exception as e:
                stream_state["error"] = e
                raise
        
        # 添加后台任务记录日志
        background_tasks.add_task(
            log_streaming_completion,
            stream_state,
            provider,
            request,
            ...
        )
        
        return StreamingResponse(tracked_stream(), ...)
```

### 方案 2: 使用 asyncio.create_task

在 generator 外部创建异步任务:

```python
async def route_streaming_request(...):
    # 创建共享状态
    stream_state = {
        "last_chunk": None,
        "completed": asyncio.Event()
    }
    
    async def log_after_stream():
        await stream_state["completed"].wait()
        # 记录日志
        await self._log_streaming_request(...)
    
    # 启动后台任务
    log_task = asyncio.create_task(log_after_stream())
    
    try:
        async for chunk in ...:
            stream_state["last_chunk"] = chunk
            yield chunk
    finally:
        stream_state["completed"].set()
        await log_task  # 确保日志任务完成
```

### 方案 3: 改用中间件

在 FastAPI 中间件层面拦截响应:

```python
@app.middleware("http")
async def log_streaming_middleware(request: Request, call_next):
    response = await call_next(request)
    
    if isinstance(response, StreamingResponse):
        # 包装响应流并记录
        ...
    
    return response
```

## 立即临时解决方案

**最简单的修复** - 在 `chat.py` 中添加日志回调:

```python
# chat.py:114-130
if request.stream:
    # 创建追踪状态
    stream_state = {"last_chunk": None}
    
    async def tracked_generator():
        try:
            async for chunk in router_service.route_streaming_request(...):
                if chunk.startswith("data: ") and not chunk.startswith("data: [DONE]"):
                    stream_state["last_chunk"] = chunk
                yield chunk
        finally:
            # 流结束后立即记录
            if stream_state["last_chunk"]:
                # 提取 usage 并记录日志
                asyncio.create_task(
                    log_streaming_usage(stream_state["last_chunk"], provider, request)
                )
    
    return StreamingResponse(tracked_generator(), ...)
```

## 推荐实施步骤

1. **立即修复**: 使用方案 1(后台任务)
2. **验证**: 运行 test_streaming_token_fix.sh
3. **监控**: 检查日志中是否有 "Streaming request logged"
4. **确认**: 查询数据库验证 Token 统计非零

## 代码位置

需要修改的文件:
- `app/api/routes/chat.py:114-130` - 添加后台任务
- `app/services/router.py:224-328` - 移除无效的日志记录代码

## 警告

**不要尝试在 generator 内部的 finally 块中执行数据库操作!**

这会导致:
- 语法错误或运行时错误
- 数据库连接问题
- 日志仍然不会被记录

必须使用上述方案之一,在 generator 外部处理日志记录。