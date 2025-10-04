"""
Excel Import/Export API routes
"""
from typing import Optional
from io import BytesIO

from fastapi import APIRouter, Depends, UploadFile, File, Query, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_database, verify_admin_key
from app.services.excel_service import ExcelService
from app.core.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/admin/excel", tags=["excel"])


@router.get(
    "/export/providers",
    dependencies=[Depends(verify_admin_key)]
)
async def export_providers(db: AsyncSession = Depends(get_database)):
    """导出提供商列表到 Excel"""
    logger.info("Export providers request received")
    
    try:
        service = ExcelService(db)
        excel_file = await service.export_providers()
        
        return StreamingResponse(
            excel_file,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": "attachment; filename=providers.xlsx"
            }
        )
    except Exception as e:
        logger.error(f"Failed to export providers: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export providers: {str(e)}"
        )


@router.get(
    "/export/models",
    dependencies=[Depends(verify_admin_key)]
)
async def export_models(db: AsyncSession = Depends(get_database)):
    """导出模型配置到 Excel"""
    logger.info("Export models request received")
    
    try:
        service = ExcelService(db)
        excel_file = await service.export_models()
        
        return StreamingResponse(
            excel_file,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": "attachment; filename=models.xlsx"
            }
        )
    except Exception as e:
        logger.error(f"Failed to export models: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export models: {str(e)}"
        )


@router.get(
    "/export/mappings",
    dependencies=[Depends(verify_admin_key)]
)
async def export_model_mappings(db: AsyncSession = Depends(get_database)):
    """导出模型映射关系到 Excel"""
    logger.info("Export model mappings request received")
    
    try:
        service = ExcelService(db)
        excel_file = await service.export_model_mappings()
        
        return StreamingResponse(
            excel_file,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": "attachment; filename=model_mappings.xlsx"
            }
        )
    except Exception as e:
        logger.error(f"Failed to export model mappings: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export model mappings: {str(e)}"
        )


@router.get(
    "/export/all",
    dependencies=[Depends(verify_admin_key)]
)
async def export_all(db: AsyncSession = Depends(get_database)):
    """导出所有数据到 Excel (多个工作表)"""
    logger.info("Export all data request received")
    
    try:
        service = ExcelService(db)
        excel_file = await service.export_all()
        
        return StreamingResponse(
            excel_file,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": "attachment; filename=llm_orchestrator_data.xlsx"
            }
        )
    except Exception as e:
        logger.error(f"Failed to export all data: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export all data: {str(e)}"
        )


@router.post(
    "/import/providers",
    dependencies=[Depends(verify_admin_key)]
)
async def import_providers(
    file: UploadFile = File(...),
    skip_duplicates: bool = Query(True, description="跳过重复的提供商"),
    db: AsyncSession = Depends(get_database)
):
    """从 Excel 导入提供商"""
    logger.info(f"Import providers request received: {file.filename}")
    
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="只支持 Excel 文件 (.xlsx, .xls)"
        )
    
    try:
        # 读取文件内容
        content = await file.read()
        excel_file = BytesIO(content)
        
        service = ExcelService(db)
        result = await service.import_providers(excel_file, skip_duplicates)
        
        return {
            "success": True,
            "message": f"导入完成: 创建 {result['created']} 个, 跳过 {result['skipped']} 个",
            "details": result
        }
    except Exception as e:
        logger.error(f"Failed to import providers: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"导入失败: {str(e)}"
        )


@router.post(
    "/import/models",
    dependencies=[Depends(verify_admin_key)]
)
async def import_models(
    file: UploadFile = File(...),
    skip_duplicates: bool = Query(True, description="跳过重复的模型"),
    db: AsyncSession = Depends(get_database)
):
    """从 Excel 导入模型配置"""
    logger.info(f"Import models request received: {file.filename}")
    
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="只支持 Excel 文件 (.xlsx, .xls)"
        )
    
    try:
        # 读取文件内容
        content = await file.read()
        excel_file = BytesIO(content)
        
        service = ExcelService(db)
        result = await service.import_models(excel_file, skip_duplicates)
        
        return {
            "success": True,
            "message": f"导入完成: 创建 {result['created']} 个, 跳过 {result['skipped']} 个",
            "details": result
        }
    except Exception as e:
        logger.error(f"Failed to import models: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"导入失败: {str(e)}"
        )


@router.get(
    "/template/providers",
    dependencies=[Depends(verify_admin_key)]
)
async def download_provider_template():
    """下载提供商导入模板"""
    import pandas as pd
    
    # 创建模板
    template_data = [{
        '名称': 'example-provider',
        '类型': 'openai',
        'API密钥': 'sk-xxx',
        '基础URL': 'https://api.openai.com/v1',
        '优先级': 100,
        '启用状态': '是'
    }]
    
    df = pd.DataFrame(template_data)
    
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='提供商模板', index=False)
    
    output.seek(0)
    
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": "attachment; filename=provider_template.xlsx"
        }
    )


@router.get(
    "/template/models",
    dependencies=[Depends(verify_admin_key)]
)
async def download_model_template():
    """下载模型配置导入模板"""
    import pandas as pd
    
    # 创建模板
    template_data = [{
        '模型名称': 'gpt-3.5-turbo',
        '显示名称': 'GPT-3.5 Turbo',
        '上下文长度': 4096,
        '最大Tokens': 4096,
        '输入成本(每百万)': 0.5,
        '输出成本(每百万)': 1.5,
        '支持流式': '是',
        '支持函数': '是',
        '支持视觉': '否'
    }]
    
    df = pd.DataFrame(template_data)
    
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='模型配置模板', index=False)
    
    output.seek(0)
    
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": "attachment; filename=model_template.xlsx"
        }
    )