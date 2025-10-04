"""
数据模型测试
"""
import pytest
from datetime import datetime, UTC
from sqlalchemy import select

from app.models.provider import Provider, ModelConfig, ModelProvider
from app.models.request_log import RequestLog
from app.models.health import ProviderHealth


@pytest.mark.asyncio
class TestProviderModel:
    """Provider 模型测试"""
    
    async def test_create_provider(self, test_session):
        """测试创建提供商"""
        provider = Provider(
            name="test-provider",
            type="openai",
            api_key="sk-test",
            base_url="https://api.openai.com/v1",
            priority=100,
            enabled=True
        )
        
        test_session.add(provider)
        await test_session.commit()
        await test_session.refresh(provider)
        
        assert provider.id is not None
        assert provider.name == "test-provider"
        assert provider.type == "openai"
        assert provider.enabled is True
    
    async def test_provider_unique_name(self, test_session):
        """测试提供商名称唯一性"""
        provider1 = Provider(
            name="duplicate-provider",
            type="openai",
            api_key="sk-test1",
            priority=100
        )
        provider2 = Provider(
            name="duplicate-provider",
            type="anthropic",
            api_key="sk-test2",
            priority=90
        )
        
        test_session.add(provider1)
        await test_session.commit()
        
        test_session.add(provider2)
        with pytest.raises(Exception):  # 违反唯一约束
            await test_session.commit()


@pytest.mark.asyncio
class TestModelConfigModel:
    """ModelConfig 模型测试"""
    
    async def test_create_model_config(self, test_session):
        """测试创建模型配置"""
        model = ModelConfig(
            name="gpt-3.5-turbo",
            display_name="GPT-3.5 Turbo",
            context_length=4096,
            max_tokens=4096,
            input_cost_per_million=0.5,
            output_cost_per_million=1.5,
            supports_streaming=True,
            supports_functions=True
        )
        
        test_session.add(model)
        await test_session.commit()
        await test_session.refresh(model)
        
        assert model.id is not None
        assert model.name == "gpt-3.5-turbo"
        assert model.context_length == 4096
        assert model.supports_streaming is True


@pytest.mark.asyncio
class TestModelProviderRelation:
    """ModelProvider 关系测试"""
    
    async def test_model_provider_mapping(self, test_session):
        """测试模型与提供商映射"""
        # 创建提供商
        provider = Provider(
            name="test-provider",
            type="openai",
            api_key="sk-test",
            priority=100
        )
        test_session.add(provider)
        await test_session.commit()
        
        # 创建模型
        model = ModelConfig(
            name="gpt-3.5-turbo",
            display_name="GPT-3.5 Turbo",
            context_length=4096
        )
        test_session.add(model)
        await test_session.commit()
        
        # 创建映射
        mapping = ModelProvider(
            model_id=model.id,
            provider_id=provider.id,
            provider_model_name="gpt-3.5-turbo",
            enabled=True
        )
        test_session.add(mapping)
        await test_session.commit()
        
        assert mapping.id is not None
        assert mapping.model_id == model.id
        assert mapping.provider_id == provider.id


@pytest.mark.asyncio
class TestRequestLogModel:
    """RequestLog 模型测试"""
    
    async def test_create_request_log(self, test_session):
        """测试创建请求日志"""
        log = RequestLog(
            request_id="test-123",
            model="gpt-3.5-turbo",
            provider_id=1,
            prompt_tokens=10,
            completion_tokens=20,
            total_tokens=30,
            latency_ms=500,
            success=True
        )
        
        test_session.add(log)
        await test_session.commit()
        await test_session.refresh(log)
        
        assert log.id is not None
        assert log.request_id == "test-123"
        assert log.total_tokens == 30
        assert log.success is True
        assert log.created_at is not None


@pytest.mark.asyncio
class TestProviderHealthModel:
    """ProviderHealth 模型测试"""
    
    async def test_create_health_record(self, test_session):
        """测试创建健康记录"""
        health = ProviderHealth(
            provider_id=1,
            is_healthy=True,
            response_time_ms=200,
            error_rate=0.01,
            success_rate=0.99,
            last_check_at=datetime.now(UTC)
        )
        
        test_session.add(health)
        await test_session.commit()
        await test_session.refresh(health)
        
        assert health.id is not None
        assert health.is_healthy is True
        assert health.response_time_ms == 200
        assert health.success_rate == 0.99