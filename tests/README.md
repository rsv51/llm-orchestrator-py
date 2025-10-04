# 测试文档

本目录包含 LLM Orchestrator 的单元测试和集成测试。

## 目录结构

```
tests/
├── __init__.py          # 测试包初始化
├── conftest.py          # Pytest 配置和 fixtures
├── test_api.py          # API 路由测试
├── test_models.py       # 数据模型测试
├── test_services.py     # 服务层测试
└── README.md            # 本文档
```

## 运行测试

### 安装测试依赖

```bash
pip install -r requirements.txt
```

测试所需的主要依赖:
- `pytest` - 测试框架
- `pytest-asyncio` - 异步测试支持
- `pytest-cov` - 代码覆盖率
- `httpx` - HTTP 客户端测试

### 运行所有测试

```bash
# 基本运行
pytest

# 详细输出
pytest -v

# 显示打印输出
pytest -s
```

### 运行特定测试

```bash
# 运行特定文件
pytest tests/test_api.py

# 运行特定测试类
pytest tests/test_api.py::TestHealthEndpoint

# 运行特定测试方法
pytest tests/test_api.py::TestHealthEndpoint::test_health_check

# 运行带标记的测试
pytest -m unit
pytest -m integration
pytest -m asyncio
```

### 代码覆盖率

```bash
# 生成覆盖率报告
pytest --cov=app --cov-report=html

# 查看 HTML 报告
# 在浏览器中打开 htmlcov/index.html

# 终端输出覆盖率
pytest --cov=app --cov-report=term-missing
```

## 测试配置

测试配置在 [`pytest.ini`](../pytest.ini) 中定义:

- **测试路径**: `tests/`
- **覆盖率目标**: 70%
- **异步模式**: 自动
- **日志级别**: INFO

## Fixtures

在 [`conftest.py`](conftest.py) 中定义了共享的 fixtures:

### 数据库 Fixtures

- `test_engine` - 测试数据库引擎 (SQLite 内存数据库)
- `test_session` - 测试数据库会话
- `test_client` - 测试 HTTP 客户端

### 模拟数据 Fixtures

- `mock_openai_response` - 模拟 OpenAI API 响应
- `mock_streaming_response` - 模拟流式响应

### 使用示例

```python
@pytest.mark.asyncio
async def test_example(test_session, test_client):
    """示例测试"""
    # 使用 test_session 进行数据库操作
    provider = Provider(name="test", type="openai", api_key="sk-test")
    test_session.add(provider)
    await test_session.commit()
    
    # 使用 test_client 进行 API 请求
    response = await test_client.get("/health")
    assert response.status_code == 200
```

## 测试类型

### 单元测试 (`@pytest.mark.unit`)

测试独立的函数、类和方法:

```python
@pytest.mark.unit
def test_weighted_selection():
    """测试加权选择逻辑"""
    balancer = LoadBalancer()
    # ... 测试逻辑
```

### 集成测试 (`@pytest.mark.integration`)

测试组件之间的交互:

```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_provider_health_check(test_session):
    """测试提供商健康检查流程"""
    # ... 测试逻辑
```

### 异步测试 (`@pytest.mark.asyncio`)

测试异步函数和协程:

```python
@pytest.mark.asyncio
async def test_async_operation(test_client):
    """测试异步操作"""
    response = await test_client.get("/endpoint")
    assert response.status_code == 200
```

## 测试覆盖范围

### API 路由测试 (`test_api.py`)

- ✅ 健康检查端点
- ✅ 模型列表端点 (认证测试)
- ✅ 聊天完成端点 (请求验证)
- ✅ 管理员端点 (认证测试)

### 数据模型测试 (`test_models.py`)

- ✅ Provider 模型创建和约束
- ✅ ModelConfig 模型创建
- ✅ ModelProvider 关系映射
- ✅ RequestLog 日志记录
- ✅ ProviderHealth 健康记录

### 服务层测试 (`test_services.py`)

- ✅ LoadBalancer 负载均衡逻辑
- ✅ RequestRouter 请求路由
- ✅ HealthCheckService 健康检查
- ✅ 加权随机选择算法

## 编写新测试

### 测试命名规范

- 测试文件: `test_*.py`
- 测试类: `Test*`
- 测试方法: `test_*`

### 测试结构

```python
@pytest.mark.asyncio  # 异步测试标记
class TestYourFeature:
    """功能描述"""
    
    async def test_success_case(self, test_session):
        """测试成功情况"""
        # Arrange (准备)
        data = prepare_test_data()
        
        # Act (执行)
        result = await perform_operation(data)
        
        # Assert (断言)
        assert result.success is True
        assert result.value == expected_value
    
    async def test_error_case(self, test_session):
        """测试错误情况"""
        with pytest.raises(ExpectedException):
            await perform_invalid_operation()
```

### 使用 Mock

```python
from unittest.mock import Mock, AsyncMock, patch

@patch('app.services.router.LoadBalancer.select_provider')
async def test_with_mock(mock_select):
    """使用 mock 的测试"""
    mock_select.return_value = mock_provider
    
    result = await service.method()
    assert result is not None
    mock_select.assert_called_once()
```

## 最佳实践

### 1. 测试隔离

每个测试应该独立运行,不依赖其他测试的状态:

```python
async def test_isolated(test_session):
    """隔离的测试"""
    # 清理可能存在的数据
    await test_session.execute(delete(Provider))
    
    # 创建测试数据
    provider = Provider(...)
    test_session.add(provider)
    await test_session.commit()
```

### 2. 使用 Fixtures

复用测试数据和设置:

```python
@pytest.fixture
async def sample_provider(test_session):
    """示例提供商 fixture"""
    provider = Provider(
        name="sample",
        type="openai",
        api_key="sk-test"
    )
    test_session.add(provider)
    await test_session.commit()
    return provider

async def test_with_fixture(sample_provider):
    """使用 fixture 的测试"""
    assert sample_provider.name == "sample"
```

### 3. 清晰的断言

使用清晰、具体的断言消息:

```python
async def test_validation(test_client):
    """测试验证逻辑"""
    response = await test_client.post("/endpoint", json={})
    
    assert response.status_code == 422, "应该返回验证错误"
    data = response.json()
    assert "detail" in data, "响应应包含错误详情"
```

### 4. 测试边界条件

测试正常情况和边界情况:

```python
@pytest.mark.parametrize("priority,expected", [
    (0, False),      # 边界: 最小值
    (100, True),     # 正常值
    (1000, True),    # 边界: 大值
    (-1, False),     # 异常: 负值
])
async def test_priority_validation(priority, expected):
    """测试优先级验证"""
    result = validate_priority(priority)
    assert result == expected
```

## 持续集成

测试可以集成到 CI/CD 流程中:

```yaml
# .github/workflows/test.yml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
      - run: pip install -r requirements.txt
      - run: pytest --cov=app --cov-report=xml
```

## 故障排查

### 测试失败

1. 查看详细输出: `pytest -v -s`
2. 检查日志: `pytest --log-cli-level=DEBUG`
3. 运行单个测试: `pytest tests/test_file.py::test_name -v`

### 导入错误

确保项目根目录在 Python 路径中:

```bash
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
pytest
```

### 异步测试问题

确保使用 `@pytest.mark.asyncio` 标记:

```python
@pytest.mark.asyncio
async def test_async_function():
    result = await async_operation()
    assert result is not None
```

## 参考资源

- [Pytest 文档](https://docs.pytest.org/)
- [Pytest-Asyncio 文档](https://pytest-asyncio.readthedocs.io/)
- [Coverage.py 文档](https://coverage.readthedocs.io/)
- [FastAPI 测试文档](https://fastapi.tiangolo.com/tutorial/testing/)