"""
Excel Import/Export Service

提供提供商、模型配置和模型映射的批量导入导出功能
"""
from typing import List, Dict, Any, Optional
from io import BytesIO
import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.provider import Provider, ModelConfig, ModelProvider
from app.core.logger import get_logger

logger = get_logger(__name__)


class ExcelService:
    """Excel 批量导入导出服务"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    # ========================================================================
    # 导出功能
    # ========================================================================
    
    async def export_providers(self) -> BytesIO:
        """
        导出提供商列表到 Excel
        
        Returns:
            BytesIO: Excel 文件的字节流
        """
        logger.info("Exporting providers to Excel")
        
        try:
            # 查询所有提供商
            query = select(Provider).order_by(Provider.priority.desc(), Provider.id)
            result = await self.db.execute(query)
            providers = result.scalars().all()
            
            # 转换为 DataFrame
            data = []
            for p in providers:
                data.append({
                    'ID': p.id,
                    '名称': p.name,
                    '类型': p.type,
                    'API密钥': p.api_key,
                    '基础URL': p.base_url or '',
                    '优先级': p.priority,
                    '启用状态': '是' if p.enabled else '否',
                    '创建时间': p.created_at.strftime('%Y-%m-%d %H:%M:%S') if p.created_at else '',
                    '更新时间': p.updated_at.strftime('%Y-%m-%d %H:%M:%S') if p.updated_at else ''
                })
            
            df = pd.DataFrame(data)
            
            # 写入 Excel
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='提供商', index=False)
            
            output.seek(0)
            logger.info(f"Exported {len(providers)} providers")
            return output
            
        except Exception as e:
            logger.error(f"Failed to export providers: {str(e)}", exc_info=True)
            raise
    
    async def export_models(self) -> BytesIO:
        """
        导出模型配置到 Excel
        
        Returns:
            BytesIO: Excel 文件的字节流
        """
        logger.info("Exporting models to Excel")
        
        try:
            # 查询所有模型
            query = select(ModelConfig).order_by(ModelConfig.id)
            result = await self.db.execute(query)
            models = result.scalars().all()
            
            # 转换为 DataFrame
            data = []
            for m in models:
                data.append({
                    'ID': m.id,
                    '模型名称': m.name,
                    '显示名称': m.display_name or m.name,
                    '上下文长度': m.context_length,
                    '最大Tokens': m.max_tokens,
                    '输入成本(每百万)': m.input_cost_per_million,
                    '输出成本(每百万)': m.output_cost_per_million,
                    '支持流式': '是' if m.supports_streaming else '否',
                    '支持函数': '是' if m.supports_functions else '否',
                    '支持视觉': '是' if m.supports_vision else '否',
                    '创建时间': m.created_at.strftime('%Y-%m-%d %H:%M:%S') if m.created_at else ''
                })
            
            df = pd.DataFrame(data)
            
            # 写入 Excel
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='模型配置', index=False)
            
            output.seek(0)
            logger.info(f"Exported {len(models)} models")
            return output
            
        except Exception as e:
            logger.error(f"Failed to export models: {str(e)}", exc_info=True)
            raise
    
    async def export_model_mappings(self) -> BytesIO:
        """
        导出模型映射关系到 Excel
        
        Returns:
            BytesIO: Excel 文件的字节流
        """
        logger.info("Exporting model mappings to Excel")
        
        try:
            # 查询所有映射关系
            query = (
                select(ModelProvider, ModelConfig, Provider)
                .join(ModelConfig, ModelProvider.model_id == ModelConfig.id)
                .join(Provider, ModelProvider.provider_id == Provider.id)
                .order_by(ModelProvider.id)
            )
            result = await self.db.execute(query)
            rows = result.all()
            
            # 转换为 DataFrame
            data = []
            for mapping, model, provider in rows:
                data.append({
                    'ID': mapping.id,
                    '模型ID': model.id,
                    '模型名称': model.name,
                    '提供商ID': provider.id,
                    '提供商名称': provider.name,
                    '提供商模型名': mapping.provider_model_name,
                    '启用状态': '是' if mapping.enabled else '否',
                    '创建时间': mapping.created_at.strftime('%Y-%m-%d %H:%M:%S') if mapping.created_at else ''
                })
            
            df = pd.DataFrame(data)
            
            # 写入 Excel
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='模型映射', index=False)
            
            output.seek(0)
            logger.info(f"Exported {len(rows)} model mappings")
            return output
            
        except Exception as e:
            logger.error(f"Failed to export model mappings: {str(e)}", exc_info=True)
            raise
    
    async def export_all(self) -> BytesIO:
        """
        导出所有数据到单个 Excel 文件(多个工作表)
        
        Returns:
            BytesIO: Excel 文件的字节流
        """
        logger.info("Exporting all data to Excel")
        
        try:
            output = BytesIO()
            
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                # 导出提供商
                query = select(Provider).order_by(Provider.priority.desc(), Provider.id)
                result = await self.db.execute(query)
                providers = result.scalars().all()
                
                provider_data = []
                for p in providers:
                    provider_data.append({
                        'ID': p.id,
                        '名称': p.name,
                        '类型': p.type,
                        'API密钥': p.api_key,
                        '基础URL': p.base_url or '',
                        '优先级': p.priority,
                        '启用状态': '是' if p.enabled else '否',
                        '创建时间': p.created_at.strftime('%Y-%m-%d %H:%M:%S') if p.created_at else ''
                    })
                
                df_providers = pd.DataFrame(provider_data)
                df_providers.to_excel(writer, sheet_name='提供商', index=False)
                
                # 导出模型配置
                query = select(ModelConfig).order_by(ModelConfig.id)
                result = await self.db.execute(query)
                models = result.scalars().all()
                
                model_data = []
                for m in models:
                    model_data.append({
                        'ID': m.id,
                        '模型名称': m.name,
                        '显示名称': m.display_name or m.name,
                        '上下文长度': m.context_length,
                        '最大Tokens': m.max_tokens,
                        '输入成本': m.input_cost_per_million,
                        '输出成本': m.output_cost_per_million,
                        '支持流式': '是' if m.supports_streaming else '否',
                        '支持函数': '是' if m.supports_functions else '否'
                    })
                
                df_models = pd.DataFrame(model_data)
                df_models.to_excel(writer, sheet_name='模型配置', index=False)
                
                # 导出模型映射
                query = (
                    select(ModelProvider, ModelConfig, Provider)
                    .join(ModelConfig, ModelProvider.model_id == ModelConfig.id)
                    .join(Provider, ModelProvider.provider_id == Provider.id)
                    .order_by(ModelProvider.id)
                )
                result = await self.db.execute(query)
                rows = result.all()
                
                mapping_data = []
                for mapping, model, provider in rows:
                    mapping_data.append({
                        'ID': mapping.id,
                        '模型名称': model.name,
                        '提供商名称': provider.name,
                        '提供商模型名': mapping.provider_model_name,
                        '启用状态': '是' if mapping.enabled else '否'
                    })
                
                df_mappings = pd.DataFrame(mapping_data)
                df_mappings.to_excel(writer, sheet_name='模型映射', index=False)
            
            output.seek(0)
            logger.info("Exported all data successfully")
            return output
            
        except Exception as e:
            logger.error(f"Failed to export all data: {str(e)}", exc_info=True)
            raise
    
    # ========================================================================
    # 导入功能
    # ========================================================================
    
    async def import_providers(self, file: BytesIO, skip_duplicates: bool = True) -> Dict[str, Any]:
        """
        从 Excel 导入提供商
        
        Args:
            file: Excel 文件的字节流
            skip_duplicates: 是否跳过重复的提供商
            
        Returns:
            导入结果统计
        """
        logger.info("Importing providers from Excel")
        
        try:
            # 读取 Excel
            df = pd.read_excel(file, sheet_name=0)
            
            created = 0
            skipped = 0
            errors = []
            
            for index, row in df.iterrows():
                try:
                    name = str(row.get('名称', ''))
                    if not name:
                        errors.append(f"行 {index + 2}: 名称不能为空")
                        continue
                    
                    # 检查是否已存在
                    query = select(Provider).where(Provider.name == name)
                    result = await self.db.execute(query)
                    existing = result.scalar_one_or_none()
                    
                    if existing and skip_duplicates:
                        skipped += 1
                        continue
                    
                    if existing:
                        errors.append(f"行 {index + 2}: 提供商 '{name}' 已存在")
                        continue
                    
                    # 创建提供商
                    provider = Provider(
                        name=name,
                        type=str(row.get('类型', 'openai')),
                        api_key=str(row.get('API密钥', '')),
                        base_url=str(row.get('基础URL', '')) if pd.notna(row.get('基础URL')) else None,
                        priority=int(row.get('优先级', 100)),
                        enabled=str(row.get('启用状态', '是')) == '是'
                    )
                    
                    self.db.add(provider)
                    created += 1
                    
                except Exception as e:
                    errors.append(f"行 {index + 2}: {str(e)}")
            
            await self.db.commit()
            
            result = {
                'created': created,
                'skipped': skipped,
                'total': len(df),
                'errors': errors
            }
            
            logger.info(f"Import completed: {result}")
            return result
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to import providers: {str(e)}", exc_info=True)
            raise
    
    async def import_models(self, file: BytesIO, skip_duplicates: bool = True) -> Dict[str, Any]:
        """
        从 Excel 导入模型配置
        
        Args:
            file: Excel 文件的字节流
            skip_duplicates: 是否跳过重复的模型
            
        Returns:
            导入结果统计
        """
        logger.info("Importing models from Excel")
        
        try:
            # 读取 Excel
            df = pd.read_excel(file, sheet_name=0)
            
            created = 0
            skipped = 0
            errors = []
            
            for index, row in df.iterrows():
                try:
                    name = str(row.get('模型名称', ''))
                    if not name:
                        errors.append(f"行 {index + 2}: 模型名称不能为空")
                        continue
                    
                    # 检查是否已存在
                    query = select(ModelConfig).where(ModelConfig.name == name)
                    result = await self.db.execute(query)
                    existing = result.scalar_one_or_none()
                    
                    if existing and skip_duplicates:
                        skipped += 1
                        continue
                    
                    if existing:
                        errors.append(f"行 {index + 2}: 模型 '{name}' 已存在")
                        continue
                    
                    # 创建模型
                    model = ModelConfig(
                        name=name,
                        display_name=str(row.get('显示名称', name)),
                        context_length=int(row.get('上下文长度', 4096)),
                        max_tokens=int(row.get('最大Tokens', 4096)),
                        input_cost_per_million=float(row.get('输入成本(每百万)', 0)),
                        output_cost_per_million=float(row.get('输出成本(每百万)', 0)),
                        supports_streaming=str(row.get('支持流式', '是')) == '是',
                        supports_functions=str(row.get('支持函数', '否')) == '是',
                        supports_vision=str(row.get('支持视觉', '否')) == '是'
                    )
                    
                    self.db.add(model)
                    created += 1
                    
                except Exception as e:
                    errors.append(f"行 {index + 2}: {str(e)}")
            
            await self.db.commit()
            
            result = {
                'created': created,
                'skipped': skipped,
                'total': len(df),
                'errors': errors
            }
            
            logger.info(f"Import completed: {result}")
            return result
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to import models: {str(e)}", exc_info=True)
            raise