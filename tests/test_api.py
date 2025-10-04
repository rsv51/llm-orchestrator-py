"""
API 路由测试
"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestHealthEndpoint:
    """健康检查端点测试"""
    
    async def test_health_check(self, test_client: AsyncClient):
        """测试健康检查端点"""
        response = await test_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data


@pytest.mark.asyncio
class TestModelsEndpoint:
    """模型列表端点测试"""
    
    async def test_list_models_without_auth(self, test_client: AsyncClient):
        """测试未认证的模型列表请求"""
        response = await test_client.get("/v1/models")
        assert response.status_code == 401
    
    async def test_list_models_with_auth(self, test_client: AsyncClient):
        """测试已认证的模型列表请求"""
        response = await test_client.get(
            "/v1/models",
            headers={"Authorization": "Bearer test-key"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert isinstance(data["data"], list)
    
    async def test_list_models_with_invalid_auth(self, test_client: AsyncClient):
        """测试无效认证的模型列表请求"""
        response = await test_client.get(
            "/v1/models",
            headers={"Authorization": "Bearer invalid-key"}
        )
        assert response.status_code == 401


@pytest.mark.asyncio
class TestChatCompletionEndpoint:
    """聊天完成端点测试"""
    
    async def test_chat_completion_without_auth(self, test_client: AsyncClient):
        """测试未认证的聊天完成请求"""
        response = await test_client.post(
            "/v1/chat/completions",
            json={
                "model": "gpt-3.5-turbo",
                "messages": [{"role": "user", "content": "Hello"}]
            }
        )
        assert response.status_code == 401
    
    async def test_chat_completion_invalid_request(self, test_client: AsyncClient):
        """测试无效的聊天完成请求"""
        response = await test_client.post(
            "/v1/chat/completions",
            headers={"Authorization": "Bearer test-key"},
            json={"model": "gpt-3.5-turbo"}  # 缺少 messages
        )
        assert response.status_code == 422
    
    async def test_chat_completion_empty_messages(self, test_client: AsyncClient):
        """测试空消息列表"""
        response = await test_client.post(
            "/v1/chat/completions",
            headers={"Authorization": "Bearer test-key"},
            json={
                "model": "gpt-3.5-turbo",
                "messages": []
            }
        )
        assert response.status_code == 422


@pytest.mark.asyncio
class TestAdminEndpoints:
    """管理员端点测试"""
    
    async def test_admin_health_without_auth(self, test_client: AsyncClient):
        """测试未认证的管理员健康检查"""
        response = await test_client.get("/admin/health")
        assert response.status_code == 401
    
    async def test_admin_providers_without_auth(self, test_client: AsyncClient):
        """测试未认证的提供商列表"""
        response = await test_client.get("/admin/providers")
        assert response.status_code == 401
    
    async def test_admin_stats_without_auth(self, test_client: AsyncClient):
        """测试未认证的统计信息"""
        response = await test_client.get("/admin/stats")
        assert response.status_code == 401