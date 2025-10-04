"""
Admin API routes for provider and system management.
"""
from typing import List, Optional
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status, File, UploadFile
from sqlalchemy import select, func, and_, case
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import (
    get_database,
    get_cache,
    verify_admin_key
)
from app.api.schemas import (
    ProviderCreate,
    ProviderUpdate,
    ProviderResponse,
    SystemHealthResponse,
    ProviderHealthStatus,
    SystemStats,
    ProviderStats,
    RequestLogResponse,
    RequestLogListResponse,
    ModelConfigCreate,
    ModelConfigUpdate,
    ModelConfigResponse,
    ErrorResponse
)
from app.core.cache import RedisCache
from app.core.logger import get_logger
from app.models.provider import Provider, ModelConfig
from app.models.request_log import RequestLog
from app.models.health import ProviderHealth, ProviderStats as DBProviderStats

logger = get_logger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])


# ============================================================================
# Authentication Test Endpoint
# ============================================================================

@router.get(
    "/verify",
    dependencies=[Depends(verify_admin_key)]
)
async def verify_admin():
    """Verify admin key - simple endpoint for login validation."""
    return {"status": "ok", "message": "Admin key is valid"}


# ============================================================================
# Provider Management
# ============================================================================

@router.get(
    "/providers",
    response_model=List[ProviderResponse],
    dependencies=[Depends(verify_admin_key)]
)
async def list_providers(
    enabled_only: bool = Query(False, description="Only return enabled providers"),
    db: AsyncSession = Depends(get_database)
):
    """List all providers."""
    logger.info("Listing providers", extra={"enabled_only": enabled_only})
    
    try:
        query = select(Provider)
        if enabled_only:
            query = query.where(Provider.enabled == True)
        query = query.order_by(Provider.priority.desc(), Provider.id)
        
        result = await db.execute(query)
        providers = result.scalars().all()
        
        return providers
    
    except Exception as e:
        logger.error(f"Failed to list providers: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list providers: {str(e)}"
        )


@router.post(
    "/providers",
    response_model=ProviderResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(verify_admin_key)]
)
async def create_provider(
    provider_data: ProviderCreate,
    db: AsyncSession = Depends(get_database),
    cache: RedisCache = Depends(get_cache)
):
    """Create a new provider."""
    logger.info(f"Creating provider: {provider_data.name}")
    
    try:
        # Check if provider already exists
        query = select(Provider).where(Provider.name == provider_data.name)
        result = await db.execute(query)
        existing = result.scalar_one_or_none()
        
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Provider {provider_data.name} already exists"
            )
        
        # Create provider
        provider = Provider(**provider_data.dict())
        db.add(provider)
        await db.commit()
        await db.refresh(provider)
        
        # Invalidate cache
        await cache.delete("providers:*")
        
        logger.info(f"Provider created: {provider.name} (ID: {provider.id})")
        return provider
    
    except HTTPException:
        raise
    
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to create provider: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create provider: {str(e)}"
        )


@router.get(
    "/providers/{provider_id}",
    response_model=ProviderResponse,
    dependencies=[Depends(verify_admin_key)]
)
async def get_provider(
    provider_id: int,
    db: AsyncSession = Depends(get_database)
):
    """Get a specific provider."""
    try:
        query = select(Provider).where(Provider.id == provider_id)
        result = await db.execute(query)
        provider = result.scalar_one_or_none()
        
        if not provider:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Provider {provider_id} not found"
            )
        
        return provider
    
    except HTTPException:
        raise
    
    except Exception as e:
        logger.error(f"Failed to get provider: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get provider: {str(e)}"
        )


@router.patch(
    "/providers/{provider_id}",
    response_model=ProviderResponse,
    dependencies=[Depends(verify_admin_key)]
)
async def update_provider(
    provider_id: int,
    provider_data: ProviderUpdate,
    db: AsyncSession = Depends(get_database),
    cache: RedisCache = Depends(get_cache)
):
    """Update a provider."""
    logger.info(f"Updating provider: {provider_id}")
    
    try:
        query = select(Provider).where(Provider.id == provider_id)
        result = await db.execute(query)
        provider = result.scalar_one_or_none()
        
        if not provider:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Provider {provider_id} not found"
            )
        
        # Update fields
        update_data = provider_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(provider, field, value)
        
        await db.commit()
        await db.refresh(provider)
        
        # Invalidate cache
        await cache.delete("providers:*")
        
        logger.info(f"Provider updated: {provider.name} (ID: {provider.id})")
        return provider
    
    except HTTPException:
        raise
    
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to update provider: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update provider: {str(e)}"
        )


@router.delete(
    "/providers/{provider_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(verify_admin_key)]
)
async def delete_provider(
    provider_id: int,
    db: AsyncSession = Depends(get_database),
    cache: RedisCache = Depends(get_cache)
):
    """Delete a provider."""
    logger.info(f"Deleting provider: {provider_id}")
    
    try:
        query = select(Provider).where(Provider.id == provider_id)
        result = await db.execute(query)
        provider = result.scalar_one_or_none()
        
        if not provider:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Provider {provider_id} not found"
            )
        
        await db.delete(provider)
        await db.commit()
        
        # Invalidate cache
        await cache.delete("providers:*")
        
        logger.info(f"Provider deleted: {provider.name} (ID: {provider_id})")
    
    except HTTPException:
        raise
    
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to delete provider: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete provider: {str(e)}"
        )


# ============================================================================
# Provider Models Management
# ============================================================================

@router.get(
    "/providers/{provider_id}/models",
    dependencies=[Depends(verify_admin_key)]
)
async def get_provider_models(
    provider_id: int,
    db: AsyncSession = Depends(get_database)
):
    """Get available models from a specific provider."""
    logger.info(f"Fetching models for provider {provider_id}")
    
    try:
        # Get provider
        query = select(Provider).where(Provider.id == provider_id)
        result = await db.execute(query)
        provider = result.scalar_one_or_none()
        
        if not provider:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Provider {provider_id} not found"
            )
        
        # Get provider instance
        from app.providers.factory import ProviderFactory
        
        provider_factory = ProviderFactory()
        provider_instance = provider_factory.create_provider(
            provider_type=provider.type,
            api_key=provider.api_key,
            base_url=provider.base_url
        )
        
        # Get models
        models = await provider_instance.get_models()
        
        return {
            "provider_id": provider_id,
            "provider_name": provider.name,
            "provider_type": provider.type,
            "models": models
        }
    
    except HTTPException:
        raise
    
    except Exception as e:
        logger.error(f"Failed to get provider models: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get provider models: {str(e)}"
        )


@router.post(
    "/providers/{provider_id}/models/import",
    dependencies=[Depends(verify_admin_key)]
)
async def import_provider_models(
    provider_id: int,
    model_names: Optional[List[str]] = None,
    db: AsyncSession = Depends(get_database),
    cache: RedisCache = Depends(get_cache)
):
    """Import models from provider to model configurations."""
    logger.info(f"Importing models from provider {provider_id}")
    
    try:
        # Get provider
        query = select(Provider).where(Provider.id == provider_id)
        result = await db.execute(query)
        provider = result.scalar_one_or_none()
        
        if not provider:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Provider {provider_id} not found"
            )
        
        # Get provider instance
        from app.providers.factory import ProviderFactory
        
        provider_factory = ProviderFactory()
        provider_instance = provider_factory.create_provider(
            provider_type=provider.type,
            api_key=provider.api_key,
            base_url=provider.base_url
        )
        
        # Get all models
        all_models = await provider_instance.get_models()
        
        # Filter models if specific names provided
        if model_names:
            models_to_import = [m for m in all_models if m in model_names]
        else:
            models_to_import = all_models
        
        imported_count = 0
        skipped_count = 0
        
        for model_name in models_to_import:
            # Check if model already exists
            query = select(ModelConfig).where(ModelConfig.name == model_name)
            result = await db.execute(query)
            existing = result.scalar_one_or_none()
            
            if existing:
                skipped_count += 1
                continue
            
            # Create model config with simplified defaults
            model_config = ModelConfig(
                name=model_name,
                remark=f"Imported from {provider.name}",
                max_retry=3,
                timeout=30,
                enabled=True
            )
            
            db.add(model_config)
            imported_count += 1
        
        await db.commit()
        
        # Invalidate cache
        await cache.delete("models:*")
        
        logger.info(f"Imported {imported_count} models from provider {provider_id}")
        
        return {
            "message": f"Successfully imported {imported_count} models",
            "imported": imported_count,
            "skipped": skipped_count,
            "total": len(models_to_import)
        }
    
    except HTTPException:
        raise
    
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to import models: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to import models: {str(e)}"
        )


# ============================================================================
# System Health
# ============================================================================

@router.get(
    "/health",
    response_model=SystemHealthResponse,
    dependencies=[Depends(verify_admin_key)]
)
async def get_system_health(
    db: AsyncSession = Depends(get_database),
    cache: RedisCache = Depends(get_cache)
):
    """Get system health status."""
    logger.info("System health check requested")
    
    try:
        # Get all providers first
        providers_query = select(Provider).order_by(Provider.priority.desc())
        providers_result = await db.execute(providers_query)
        all_providers = providers_result.scalars().all()
        
        # Ensure ProviderHealth records exist for all providers
        for provider in all_providers:
            health_query = select(ProviderHealth).where(ProviderHealth.provider_id == provider.id)
            health_result = await db.execute(health_query)
            health_record = health_result.scalar_one_or_none()
            
            if not health_record:
                # Create default health record
                health_record = ProviderHealth(
                    provider_id=provider.id,
                    is_healthy=True,
                    response_time_ms=0.0,
                    error_message=None,
                    last_check=datetime.utcnow(),
                    consecutive_failures=0,
                    success_rate=100.0
                )
                db.add(health_record)
                logger.info(f"Created health record for provider {provider.name}")
        
        await db.commit()
        
        # Get provider health statuses
        query = (
            select(ProviderHealth, Provider)
            .join(Provider, ProviderHealth.provider_id == Provider.id)
            .order_by(Provider.priority.desc())
        )
        result = await db.execute(query)
        rows = result.all()
        
        provider_statuses = []
        healthy_count = 0
        
        for health, provider in rows:
            status_obj = ProviderHealthStatus(
                provider_id=provider.id,
                provider_name=provider.name,
                is_healthy=health.is_healthy,
                response_time_ms=health.response_time_ms,
                error_message=health.error_message,
                last_check=health.last_check,
                consecutive_failures=health.consecutive_failures,
                success_rate=health.success_rate
            )
            provider_statuses.append(status_obj)
            
            if health.is_healthy:
                healthy_count += 1
        
        # Determine overall system status
        total_providers = len(provider_statuses)
        if total_providers == 0:
            system_status = "unhealthy"
        elif healthy_count == total_providers:
            system_status = "healthy"
        elif healthy_count > 0:
            system_status = "degraded"
        else:
            system_status = "unhealthy"
        
        # Check database
        try:
            await db.execute(select(1))
            db_status = "healthy"
        except Exception:
            db_status = "unhealthy"
        
        # Check cache
        try:
            await cache.set("health:check", "ok", ttl=5)
            cache_status = "healthy"
        except Exception:
            cache_status = "unhealthy"
        
        return SystemHealthResponse(
            status=system_status,
            timestamp=datetime.utcnow(),
            providers=provider_statuses,
            database_status=db_status,
            cache_status=cache_status
        )
    
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Health check failed: {str(e)}"
        )


# ============================================================================
# Statistics
# ============================================================================

@router.get(
    "/stats",
    response_model=SystemStats,
    dependencies=[Depends(verify_admin_key)]
)
async def get_system_stats(
    hours: int = Query(24, ge=1, le=168, description="Time range in hours"),
    db: AsyncSession = Depends(get_database)
):
    """Get system statistics."""
    logger.info(f"System stats requested for last {hours} hours")
    
    try:
        since = datetime.utcnow() - timedelta(hours=hours)
        
        # Get overall stats
        query = select(
            func.count(RequestLog.id).label("total"),
            func.sum(
                case(
                    (RequestLog.status_code == 200, 1),
                    else_=0
                )
            ).label("success"),
            func.avg(RequestLog.latency_ms).label("avg_latency")
        ).where(RequestLog.created_at >= since)
        
        result = await db.execute(query)
        row = result.first()
        
        total_requests = row.total or 0
        successful_requests = row.success or 0
        failed_requests = total_requests - successful_requests
        success_rate = (successful_requests / total_requests * 100) if total_requests > 0 else 0
        avg_response_time = row.avg_latency or 0
        
        # Get per-provider stats
        query = (
            select(
                Provider.id,
                Provider.name,
                func.count(RequestLog.id).label("total"),
                func.sum(case((RequestLog.status_code == 200, 1), else_=0)).label("success"),
                func.avg(RequestLog.latency_ms).label("avg_latency"),
                func.sum(func.coalesce(RequestLog.total_tokens, 0)).label("total_tokens"),
                func.sum(func.coalesce(RequestLog.cost, 0)).label("total_cost")
            )
            .join(RequestLog, RequestLog.provider_id == Provider.id)
            .where(RequestLog.created_at >= since)
            .group_by(Provider.id, Provider.name)
        )
        
        result = await db.execute(query)
        rows = result.all()
        
        provider_stats = []
        for row in rows:
            total = row.total or 0
            success = row.success or 0
            failed = total - success
            
            stats = ProviderStats(
                provider_id=row.id,
                provider_name=row.name,
                total_requests=total,
                successful_requests=success,
                failed_requests=failed,
                success_rate=(success / total * 100) if total > 0 else 0,
                avg_response_time_ms=row.avg_latency or 0,
                total_tokens=row.total_tokens or 0,
                total_cost=row.total_cost or 0
            )
            provider_stats.append(stats)
        
        return SystemStats(
            total_requests=total_requests,
            successful_requests=successful_requests,
            failed_requests=failed_requests,
            success_rate=success_rate,
            avg_response_time_ms=avg_response_time,
            providers=provider_stats,
            timestamp=datetime.utcnow()
        )
    
    except Exception as e:
        logger.error(f"Failed to get stats: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get stats: {str(e)}"
        )


# ============================================================================
# Request Logs
# ============================================================================

@router.get(
    "/logs",
    response_model=RequestLogListResponse,
    dependencies=[Depends(verify_admin_key)]
)
async def get_request_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    provider_id: Optional[int] = Query(None),
    status_code: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_database)
):
    """Get request logs with pagination."""
    logger.info(f"Request logs requested: page={page}, size={page_size}")
    
    try:
        # Build query
        query = select(RequestLog, Provider).join(Provider, RequestLog.provider_id == Provider.id)
        
        if provider_id:
            query = query.where(RequestLog.provider_id == provider_id)
        if status_code:
            query = query.where(RequestLog.status_code == status_code)
        
        # Get total count
        count_query = select(func.count()).select_from(RequestLog)
        if provider_id:
            count_query = count_query.where(RequestLog.provider_id == provider_id)
        if status_code:
            count_query = count_query.where(RequestLog.status_code == status_code)
        
        result = await db.execute(count_query)
        total = result.scalar()
        
        # Get page data
        query = query.order_by(RequestLog.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)
        
        result = await db.execute(query)
        rows = result.all()
        
        logs = []
        for log, provider in rows:
            log_response = RequestLogResponse(
                id=log.id,
                provider_id=log.provider_id,
                provider_name=provider.name,
                model=log.model,
                endpoint=log.endpoint,
                method=log.method,
                status_code=log.status_code,
                prompt_tokens=log.prompt_tokens,
                completion_tokens=log.completion_tokens,
                total_tokens=log.total_tokens,
                cost=log.cost,
                latency_ms=log.latency_ms,
                error_message=log.error_message,
                user_id=log.user_id,
                ip_address=log.ip_address,
                created_at=log.created_at
            )
            logs.append(log_response)
        
        return RequestLogListResponse(
            total=total,
            page=page,
            page_size=page_size,
            logs=logs
        )
    
    except Exception as e:
        logger.error(f"Failed to get logs: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get logs: {str(e)}"
        )


# ============================================================================
# Model Configuration Management
# ============================================================================

@router.get(
    "/models",
    response_model=List[ModelConfigResponse],
    dependencies=[Depends(verify_admin_key)]
)
async def list_model_configs(
    db: AsyncSession = Depends(get_database)
):
    """List all model configurations."""
    logger.info("Listing model configurations")
    
    try:
        query = select(ModelConfig).order_by(ModelConfig.name)
        result = await db.execute(query)
        models = result.scalars().all()
        
        return models
    
    except Exception as e:
        logger.error(f"Failed to list models: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list models: {str(e)}"
        )


@router.post(
    "/models",
    response_model=ModelConfigResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(verify_admin_key)]
)
async def create_model_config(
    model_data: ModelConfigCreate,
    db: AsyncSession = Depends(get_database),
    cache: RedisCache = Depends(get_cache)
):
    """Create a new model configuration."""
    logger.info(f"Creating model config: {model_data.name}")
    
    try:
        # Check if model already exists
        query = select(ModelConfig).where(ModelConfig.name == model_data.name)
        result = await db.execute(query)
        existing = result.scalar_one_or_none()
        
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Model {model_data.name} already exists"
            )
        
        # Create model config
        model = ModelConfig(**model_data.dict())
        db.add(model)
        await db.commit()
        await db.refresh(model)
        
        # Invalidate cache
        await cache.delete("models:*")
        
        logger.info(f"Model config created: {model.name} (ID: {model.id})")
        return model
    
    except HTTPException:
        raise
    
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to create model: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create model: {str(e)}"
        )


@router.get(
    "/models/{model_id}",
    response_model=ModelConfigResponse,
    dependencies=[Depends(verify_admin_key)]
)
async def get_model_config(
    model_id: int,
    db: AsyncSession = Depends(get_database)
):
    """Get a specific model configuration."""
    try:
        query = select(ModelConfig).where(ModelConfig.id == model_id)
        result = await db.execute(query)
        model = result.scalar_one_or_none()
        
        if not model:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Model {model_id} not found"
            )
        
        return model
    
    except HTTPException:
        raise
    
    except Exception as e:
        logger.error(f"Failed to get model: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get model: {str(e)}"
        )


@router.patch(
    "/models/{model_id}",
    response_model=ModelConfigResponse,
    dependencies=[Depends(verify_admin_key)]
)
async def update_model_config(
    model_id: int,
    model_data: ModelConfigUpdate,
    db: AsyncSession = Depends(get_database),
    cache: RedisCache = Depends(get_cache)
):
    """Update a model configuration."""
    logger.info(f"Updating model config: {model_id}")
    
    try:
        query = select(ModelConfig).where(ModelConfig.id == model_id)
        result = await db.execute(query)
        model = result.scalar_one_or_none()
        
        if not model:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Model {model_id} not found"
            )
        
        # Update fields
        update_data = model_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(model, field, value)
        
        await db.commit()
        await db.refresh(model)
        
        # Invalidate cache
        await cache.delete("models:*")
        
        logger.info(f"Model config updated: {model.name} (ID: {model.id})")
        return model
    
    except HTTPException:
        raise
    
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to update model: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update model: {str(e)}"
        )


@router.delete(
    "/models/{model_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(verify_admin_key)]
)
async def delete_model_config(
    model_id: int,
    db: AsyncSession = Depends(get_database),
    cache: RedisCache = Depends(get_cache)
):
    """Delete a model configuration."""
    logger.info(f"Deleting model config: {model_id}")
    
    try:
        query = select(ModelConfig).where(ModelConfig.id == model_id)
        result = await db.execute(query)
        model = result.scalar_one_or_none()
        
        if not model:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Model {model_id} not found"
            )
        
        await db.delete(model)
        await db.commit()
        
        # Invalidate cache
        await cache.delete("models:*")
        
        logger.info(f"Model config deleted: {model.name} (ID: {model_id})")
    
    except HTTPException:
        raise
    
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to delete model: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete model: {str(e)}"
        )


# ============================================================================
# Model-Provider Association Management
# ============================================================================

@router.get(
    "/model-providers",
    dependencies=[Depends(verify_admin_key)]
)
async def list_model_providers(
    model_id: Optional[int] = Query(None),
    provider_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_database)
):
    """List model-provider associations with optional filters."""
    logger.info(f"Listing model-provider associations: model_id={model_id}, provider_id={provider_id}")
    
    try:
        from app.models.provider import ModelProvider
        
        # Build query
        query = (
            select(ModelProvider, ModelConfig, Provider)
            .join(ModelConfig, ModelProvider.model_id == ModelConfig.id)
            .join(Provider, ModelProvider.provider_id == Provider.id)
        )
        
        if model_id:
            query = query.where(ModelProvider.model_id == model_id)
        if provider_id:
            query = query.where(ModelProvider.provider_id == provider_id)
        
        query = query.order_by(ModelConfig.name, Provider.name)
        
        result = await db.execute(query)
        rows = result.all()
        
        associations = []
        for assoc, model, provider in rows:
            associations.append({
                "id": assoc.id,
                "model_id": assoc.model_id,
                "model_name": model.name,
                "provider_id": assoc.provider_id,
                "provider_name": provider.name,
                "provider_type": provider.type,
                "provider_model": assoc.provider_model,
                "weight": assoc.weight,
                "tool_call": assoc.tool_call,
                "structured_output": assoc.structured_output,
                "image": assoc.image,
                "enabled": assoc.enabled,
                "created_at": assoc.created_at,
                "updated_at": assoc.updated_at
            })
        
        return associations
    
    except Exception as e:
        logger.error(f"Failed to list model-providers: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list model-providers: {str(e)}"
        )


@router.post(
    "/model-providers",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(verify_admin_key)]
)
async def create_model_provider(
    association_data: dict,
    db: AsyncSession = Depends(get_database),
    cache: RedisCache = Depends(get_cache)
):
    """Create a new model-provider association."""
    logger.info(f"Creating model-provider association")
    
    try:
        from app.models.provider import ModelProvider
        
        # Validate model exists
        query = select(ModelConfig).where(ModelConfig.id == association_data["model_id"])
        result = await db.execute(query)
        model = result.scalar_one_or_none()
        if not model:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Model {association_data['model_id']} not found"
            )
        
        # Validate provider exists
        query = select(Provider).where(Provider.id == association_data["provider_id"])
        result = await db.execute(query)
        provider = result.scalar_one_or_none()
        if not provider:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Provider {association_data['provider_id']} not found"
            )
        
        # Check for duplicate
        query = select(ModelProvider).where(
            and_(
                ModelProvider.model_id == association_data["model_id"],
                ModelProvider.provider_id == association_data["provider_id"],
                ModelProvider.provider_model == association_data["provider_model"]
            )
        )
        result = await db.execute(query)
        existing = result.scalar_one_or_none()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This model-provider association already exists"
            )
        
        # Create association
        association = ModelProvider(
            model_id=association_data["model_id"],
            provider_id=association_data["provider_id"],
            provider_model=association_data["provider_model"],
            weight=association_data.get("weight", 1),
            tool_call=association_data.get("tool_call", True),
            structured_output=association_data.get("structured_output", True),
            image=association_data.get("image", False),
            enabled=association_data.get("enabled", True)
        )
        
        db.add(association)
        await db.commit()
        await db.refresh(association)
        
        # Invalidate cache
        await cache.delete("model-providers:*")
        
        logger.info(f"Model-provider association created: ID {association.id}")
        
        return {
            "id": association.id,
            "model_id": association.model_id,
            "provider_id": association.provider_id,
            "provider_model": association.provider_model,
            "weight": association.weight,
            "tool_call": association.tool_call,
            "structured_output": association.structured_output,
            "image": association.image,
            "enabled": association.enabled,
            "created_at": association.created_at,
            "updated_at": association.updated_at
        }
    
    except HTTPException:
        raise
    
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to create model-provider: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create model-provider: {str(e)}"
        )


@router.patch(
    "/model-providers/{association_id}",
    dependencies=[Depends(verify_admin_key)]
)
async def update_model_provider(
    association_id: int,
    association_data: dict,
    db: AsyncSession = Depends(get_database),
    cache: RedisCache = Depends(get_cache)
):
    """Update a model-provider association."""
    logger.info(f"Updating model-provider association: {association_id}")
    
    try:
        from app.models.provider import ModelProvider
        
        query = select(ModelProvider).where(ModelProvider.id == association_id)
        result = await db.execute(query)
        association = result.scalar_one_or_none()
        
        if not association:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Model-provider association {association_id} not found"
            )
        
        # Update fields
        for field, value in association_data.items():
            if hasattr(association, field):
                setattr(association, field, value)
        
        await db.commit()
        await db.refresh(association)
        
        # Invalidate cache
        await cache.delete("model-providers:*")
        
        logger.info(f"Model-provider association updated: ID {association.id}")
        
        return {
            "id": association.id,
            "model_id": association.model_id,
            "provider_id": association.provider_id,
            "provider_model": association.provider_model,
            "weight": association.weight,
            "tool_call": association.tool_call,
            "structured_output": association.structured_output,
            "image": association.image,
            "enabled": association.enabled,
            "created_at": association.created_at,
            "updated_at": association.updated_at
        }
    
    except HTTPException:
        raise
    
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to update model-provider: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update model-provider: {str(e)}"
        )


@router.delete(
    "/model-providers/{association_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(verify_admin_key)]
)
async def delete_model_provider(
    association_id: int,
    db: AsyncSession = Depends(get_database),
    cache: RedisCache = Depends(get_cache)
):
    """Delete a model-provider association."""
    logger.info(f"Deleting model-provider association: {association_id}")
    
    try:
        from app.models.provider import ModelProvider
        
        query = select(ModelProvider).where(ModelProvider.id == association_id)
        result = await db.execute(query)
        association = result.scalar_one_or_none()
        
        if not association:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Model-provider association {association_id} not found"
            )
        
        await db.delete(association)
        await db.commit()
        
        # Invalidate cache
        await cache.delete("model-providers:*")
        
        logger.info(f"Model-provider association deleted: ID {association_id}")
    
    except HTTPException:
        raise
    
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to delete model-provider: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete model-provider: {str(e)}"
        )


@router.get(
    "/model-providers/{association_id}/status",
    dependencies=[Depends(verify_admin_key)]
)
async def get_model_provider_status(
    association_id: int,
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_database)
):
    """Get recent status history for a model-provider association (like llmio-master)."""
    logger.info(f"Getting status for model-provider {association_id}")
    
    try:
        from app.models.provider import ModelProvider
        
        # Get association details
        query = (
            select(ModelProvider, ModelConfig, Provider)
            .join(ModelConfig, ModelProvider.model_id == ModelConfig.id)
            .join(Provider, ModelProvider.provider_id == Provider.id)
            .where(ModelProvider.id == association_id)
        )
        result = await db.execute(query)
        row = result.first()
        
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Model-provider association {association_id} not found"
            )
        
        assoc, model, provider = row
        
        # Get recent request logs
        query = (
            select(RequestLog.status_code, RequestLog.created_at)
            .where(
                and_(
                    RequestLog.provider_id == assoc.provider_id,
                    RequestLog.model == model.name
                )
            )
            .order_by(RequestLog.created_at.desc())
            .limit(limit)
        )
        
        result = await db.execute(query)
        logs = result.all()
        
        # Build status array (true = success, false = failure)
        status_array = [log.status_code == 200 for log in reversed(logs)]
        
        return {
            "association_id": association_id,
            "model_name": model.name,
            "provider_name": provider.name,
            "provider_model": assoc.provider_model,
            "status_history": status_array,
            "total_records": len(status_array)
        }
    
    except HTTPException:
        raise
    
    except Exception as e:
        logger.error(f"Failed to get status: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get status: {str(e)}"
        )


# ============================================================================
# Excel Import/Export
# ============================================================================

@router.get(
    "/export/template",
    dependencies=[Depends(verify_admin_key)]
)
async def download_excel_template(
    with_sample: bool = Query(False, description="Include sample data"),
    db: AsyncSession = Depends(get_database)
):
    """Download Excel import template (3 sheets: Providers, Models, Associations)."""
    logger.info(f"Downloading Excel template, with_sample={with_sample}")
    
    try:
        from fastapi.responses import StreamingResponse
        from app.services.excel_service import ExcelService
        
        excel_service = ExcelService(db)
        excel_file = await excel_service.download_template(with_sample=with_sample)
        
        filename = f"llm_orchestrator_template_{'with_sample' if with_sample else 'empty'}.xlsx"
        
        return StreamingResponse(
            excel_file,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
    
    except Exception as e:
        logger.error(f"Failed to download template: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to download template: {str(e)}"
        )


@router.get(
    "/export/config",
    dependencies=[Depends(verify_admin_key)]
)
async def export_configuration(
    db: AsyncSession = Depends(get_database)
):
    """Export all configuration (providers, models, associations) to Excel."""
    logger.info("Exporting all configuration to Excel")
    
    try:
        from fastapi.responses import StreamingResponse
        from app.services.excel_service import ExcelService
        from datetime import datetime
        
        excel_service = ExcelService(db)
        excel_file = await excel_service.export_all(include_sample=False)
        
        filename = f"llm_orchestrator_config_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        
        return StreamingResponse(
            excel_file,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
    
    except Exception as e:
        logger.error(f"Failed to export configuration: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export configuration: {str(e)}"
        )


@router.post(
    "/import/config",
    dependencies=[Depends(verify_admin_key)]
)
async def import_configuration(
    file: bytes = None,
    db: AsyncSession = Depends(get_database),
    cache: RedisCache = Depends(get_cache)
):
    """Import configuration from Excel file (3 sheets: Providers, Models, Associations)."""
    logger.info("Importing configuration from Excel")
    
    try:
        from fastapi import File, UploadFile
        from io import BytesIO
        from app.services.excel_service import ExcelService
        
        if not file:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No file provided"
            )
        
        # Convert bytes to BytesIO
        file_stream = BytesIO(file)
        
        # Import data
        excel_service = ExcelService(db)
        result = await excel_service.import_all(file_stream)
        
        # Invalidate all caches
        await cache.delete("providers:*")
        await cache.delete("models:*")
        await cache.delete("model-providers:*")
        
        logger.info(f"Import completed: {result['summary']}")
        
        return {
            "message": "Configuration imported successfully",
            "result": result
        }
    
    except HTTPException:
        raise
    
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to import configuration: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to import configuration: {str(e)}"
        )


@router.post(
    "/import/config/upload",
    dependencies=[Depends(verify_admin_key)]
)
async def import_configuration_upload(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_database),
    cache: RedisCache = Depends(get_cache)
):
    """Import configuration from uploaded Excel file."""
    logger.info(f"Importing configuration from uploaded file: {file.filename}")
    
    try:
        from io import BytesIO
        from app.services.excel_service import ExcelService
        
        # Validate file extension
        if not file.filename.lower().endswith('.xlsx'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only .xlsx files are supported"
            )
        
        # Read file content
        content = await file.read()
        file_stream = BytesIO(content)
        
        # Import data
        excel_service = ExcelService(db)
        result = await excel_service.import_all(file_stream)
        
        # Invalidate all caches
        await cache.delete("providers:*")
        await cache.delete("models:*")
        await cache.delete("model-providers:*")
        
        logger.info(f"Import completed: {result['summary']}")
        
        return {
            "message": "Configuration imported successfully",
            "filename": file.filename,
            "result": result
        }
    
    except HTTPException:
        raise
    
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to import configuration: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to import configuration: {str(e)}"
        )