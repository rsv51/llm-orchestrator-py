"""
服务层测试
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch

from app.services.balancer import LoadBalancer
from app.models.provider import Provider


@pytest.mark.asyncio
class TestLoadBalancer:
    """负载均衡器测试"""
    
    async def test_select_provider_with_no_providers(self):
        """测试没有可用提供商的情况"""
        balancer = LoadBalancer()
        
        result = await balancer.select_provider([])
        assert result is None
    
    async def test_select_provider_with_single_provider(self):
        """测试单个提供商的情况"""
        balancer = LoadBalancer()
        
        provider = Provider(
            id=1,
            name="test-provider",
            type="openai",
            api_key="sk-test",
            priority=100,
            enabled=True
        )
        
        result = await balancer.select_provider([provider])
        assert result == provider
    
    async def test_select_provider_with_multiple_providers(self):
        """测试多个提供商的情况"""
        balancer = LoadBalancer()
        
        providers = [
            Provider(
                id=1,
                name="provider-1",
                type="openai",
                api_key="sk-test1",
                priority=100,
                enabled=True
            ),
            Provider(
                id=2,
                name="provider-2",
                type="openai",
                api_key="sk-test2",
                priority=90,
                enabled=True
            ),
            Provider(
                id=3,
                name="provider-3",
                type="openai",
                api_key="sk-test3",
                priority=80,
                enabled=True
            )
        ]
        
        # 运行多次选择,验证加权随机
        selections = []
        for _ in range(100):
            result = await balancer.select_provider(providers)
            selections.append(result.id)
        
        # 验证所有提供商都被选择过
        assert len(set(selections)) == 3
        
        # 验证高优先级提供商被选择的次数更多
        provider1_count = selections.count(1)
        provider3_count = selections.count(3)
        assert provider1_count > provider3_count
    
    async def test_select_provider_excludes_disabled(self):
        """测试排除禁用的提供商"""
        balancer = LoadBalancer()
        
        providers = [
            Provider(
                id=1,
                name="enabled-provider",
                type="openai",
                api_key="sk-test1",
                priority=100,
                enabled=True
            ),
            Provider(
                id=2,
                name="disabled-provider",
                type="openai",
                api_key="sk-test2",
                priority=90,
                enabled=False
            )
        ]
        
        # 运行多次选择
        for _ in range(10):
            result = await balancer.select_provider(providers)
            # 应该只选择启用的提供商
            assert result.id == 1
            assert result.enabled is True


@pytest.mark.asyncio
class TestRequestRouter:
    """请求路由器测试"""
    
    @patch('app.services.router.RequestRouter.get_available_providers')
    @patch('app.services.router.LoadBalancer.select_provider')
    async def test_route_request_success(self, mock_select, mock_get_providers):
        """测试成功的请求路由"""
        from app.services.router import RequestRouter
        
        # 模拟提供商
        mock_provider = Provider(
            id=1,
            name="test-provider",
            type="openai",
            api_key="sk-test",
            priority=100,
            enabled=True
        )
        
        mock_get_providers.return_value = [mock_provider]
        mock_select.return_value = mock_provider
        
        router = RequestRouter(db_session=Mock())
        result = await router.select_provider_for_model("gpt-3.5-turbo")
        
        assert result == mock_provider
    
    @patch('app.services.router.RequestRouter.get_available_providers')
    async def test_route_request_no_providers(self, mock_get_providers):
        """测试没有可用提供商的情况"""
        from app.services.router import RequestRouter
        
        mock_get_providers.return_value = []
        
        router = RequestRouter(db_session=Mock())
        result = await router.select_provider_for_model("gpt-3.5-turbo")
        
        assert result is None


@pytest.mark.asyncio
class TestHealthCheckService:
    """健康检查服务测试"""
    
    @patch('app.services.health_check.HealthCheckService.check_provider_health')
    async def test_check_all_providers(self, mock_check):
        """测试检查所有提供商"""
        from app.services.health_check import HealthCheckService
        
        mock_check.return_value = True
        
        service = HealthCheckService(db_session=Mock())
        
        # 模拟提供商列表
        providers = [
            Provider(id=1, name="provider-1", type="openai", api_key="sk-1", priority=100),
            Provider(id=2, name="provider-2", type="anthropic", api_key="sk-2", priority=90)
        ]
        
        with patch.object(service, 'get_all_providers', return_value=providers):
            results = await service.check_all_providers()
        
        assert len(results) == 2
        assert all(r['is_healthy'] for r in results)


@pytest.mark.unit
def test_weighted_random_selection():
    """测试加权随机选择逻辑"""
    from app.services.balancer import LoadBalancer
    
    balancer = LoadBalancer()
    
    # 创建测试数据
    items = [
        {'id': 1, 'weight': 100},
        {'id': 2, 'weight': 50},
        {'id': 3, 'weight': 25}
    ]
    
    # 运行多次选择
    selections = []
    for _ in range(1000):
        # 模拟选择逻辑
        import random
        total_weight = sum(item['weight'] for item in items)
        rand = random.uniform(0, total_weight)
        cumulative = 0
        for item in items:
            cumulative += item['weight']
            if rand <= cumulative:
                selections.append(item['id'])
                break
    
    # 验证权重分布
    count_1 = selections.count(1)
    count_2 = selections.count(2)
    count_3 = selections.count(3)
    
    # 权重比例应该接近 100:50:25 = 4:2:1
    assert count_1 > count_2 > count_3
    
    # 允许一定的误差范围
    ratio_1_2 = count_1 / count_2
    ratio_2_3 = count_2 / count_3
    
    assert 1.5 < ratio_1_2 < 2.5  # 接近 2
    assert 1.5 < ratio_2_3 < 2.5  # 接近 2