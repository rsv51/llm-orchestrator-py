"""
Models API routes (OpenAI compatible).
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_database, get_cache, verify_api_key
from app.api.schemas import Model, ModelsListResponse, ErrorResponse
from app.core.cache import RedisCache
from app.core.logger import get_logger
from app.models.provider import ModelConfig, Provider

logger = get_logger(__name__)

router = APIRouter(prefix="/v1", tags=["models"])


# ============================================================================
# Models List Endpoint
# ============================================================================

@router.get(
    "/models",
    response_model=ModelsListResponse,
    responses={
        401: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    }
)
async def list_models(
    db: AsyncSession = Depends(get_database),
    cache: RedisCache = Depends(get_cache),
    api_key: str = Depends(verify_api_key)
):
    """
    List available models (OpenAI compatible).
    
    Returns a list of all available models from enabled providers.
    Cached for performance.
    """
    logger.info("Models list requested")
    
    try:
        # Try to get from cache first
        cache_key = "models:list"
        cached_models = await cache.get(cache_key)
        
        if cached_models:
            logger.debug("Returning models list from cache")
            return ModelsListResponse(data=cached_models)
        
        # Query database for all models from enabled providers
        query = (
            select(ModelConfig, Provider)
            .join(Provider, ModelConfig.id == Provider.id)
            .where(Provider.enabled == True)
        )
        
        result = await db.execute(query)
        rows = result.all()
        
        # Build models list
        models: List[Model] = []
        for model_config, provider in rows:
            model = Model(
                id=f"{provider.name}:{model_config.name}",
                object="model",
                created=int(model_config.created_at.timestamp()),
                owned_by=provider.name
            )
            models.append(model)
        
        # Cache for 5 minutes
        await cache.set(cache_key, [m.dict() for m in models], ttl=300)
        
        logger.info(f"Returning {len(models)} models")
        return ModelsListResponse(data=models)
    
    except Exception as e:
        logger.error(f"Failed to list models: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list models: {str(e)}"
        )


# ============================================================================
# Model Retrieve Endpoint
# ============================================================================

@router.get(
    "/models/{model_id}",
    response_model=Model,
    responses={
        401: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    }
)
async def retrieve_model(
    model_id: str,
    db: AsyncSession = Depends(get_database),
    cache: RedisCache = Depends(get_cache),
    api_key: str = Depends(verify_api_key)
):
    """
    Retrieve a model (OpenAI compatible).
    
    Returns information about a specific model.
    Model ID format: `provider:model_name` or just `model_name`.
    """
    logger.info(f"Model retrieve requested: {model_id}")
    
    try:
        # Parse model ID
        if ":" in model_id:
            provider_name, model_name = model_id.split(":", 1)
        else:
            provider_name = None
            model_name = model_id
        
        # Try cache first
        cache_key = f"models:detail:{model_id}"
        cached_model = await cache.get(cache_key)
        
        if cached_model:
            logger.debug(f"Returning model {model_id} from cache")
            return Model(**cached_model)
        
        # Query database
        if provider_name:
            # Specific provider requested
            query = (
                select(ModelConfig, Provider)
                .join(Provider, ModelConfig.id == Provider.id)
                .where(
                    Provider.name == provider_name,
                    ModelConfig.name == model_name,
                    Provider.enabled == True
                )
            )
        else:
            # Any provider with this model
            query = (
                select(ModelConfig, Provider)
                .join(Provider, ModelConfig.id == Provider.id)
                .where(
                    ModelConfig.name == model_name,
                    Provider.enabled == True
                )
                .limit(1)
            )
        
        result = await db.execute(query)
        row = result.first()
        
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Model {model_id} not found"
            )
        
        model_config, provider = row
        
        model = Model(
            id=f"{provider.name}:{model_config.name}",
            object="model",
            created=int(model_config.created_at.timestamp()),
            owned_by=provider.name
        )
        
        # Cache for 5 minutes
        await cache.set(cache_key, model.dict(), ttl=300)
        
        logger.info(f"Returning model {model_id}")
        return model
    
    except HTTPException:
        raise
    
    except Exception as e:
        logger.error(
            f"Failed to retrieve model {model_id}: {str(e)}",
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve model: {str(e)}"
        )