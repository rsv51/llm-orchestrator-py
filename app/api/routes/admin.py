"""
Admin API routes for provider and system management.
"""
from typing import List, Optional
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func, and_
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
        from app.services.router import get_provider_instance
        provider_instance = get_provider_instance(provider)
        
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
        from app.services.router import get_provider_instance
        provider_instance = get_provider_instance(provider)
        
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
            
            # Create model config with defaults
            model_config = ModelConfig(
                name=model_name,
                display_name=model_name,
                context_length=8192,  # Default value
                supports_streaming=True,
                supports_functions=False,
                supports_vision=False,
                input_price_per_million=0.0,
                output_price_per_million=0.0
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
                func.case(
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
                func.sum(func.case((RequestLog.status_code == 200, 1))).label("success"),
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