"""
数据库初始化和迁移脚本

用于创建数据库表和初始化数据
"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import inspect
from app.core.database import engine, AsyncSessionLocal
from app.core.config import settings
from app.core.logger import get_logger
from app.models.provider import Base as ProviderBase
from app.models.request_log import Base as RequestLogBase
from app.models.health import Base as HealthBase

logger = get_logger(__name__)


async def check_tables_exist():
    """检查数据库表是否存在"""
    async with engine.begin() as conn:
        def _check(connection):
            inspector = inspect(connection)
            return inspector.get_table_names()
        
        tables = await conn.run_sync(_check)
        return tables


async def create_tables():
    """创建所有数据库表"""
    logger.info("开始创建数据库表...")
    
    try:
        # 检查现有表
        existing_tables = await check_tables_exist()
        logger.info(f"现有表: {existing_tables}")
        
        # 创建所有表
        async with engine.begin() as conn:
            await conn.run_sync(ProviderBase.metadata.create_all)
            await conn.run_sync(RequestLogBase.metadata.create_all)
            await conn.run_sync(HealthBase.metadata.create_all)
        
        logger.info("数据库表创建完成")
        
        # 再次检查表
        new_tables = await check_tables_exist()
        logger.info(f"创建后的表: {new_tables}")
        
        return True
    
    except Exception as e:
        logger.error(f"创建数据库表失败: {str(e)}", exc_info=True)
        return False


async def drop_tables():
    """删除所有数据库表 (危险操作!)"""
    logger.warning("警告: 即将删除所有数据库表!")
    
    try:
        async with engine.begin() as conn:
            await conn.run_sync(ProviderBase.metadata.drop_all)
            await conn.run_sync(RequestLogBase.metadata.drop_all)
            await conn.run_sync(HealthBase.metadata.drop_all)
        
        logger.info("数据库表已删除")
        return True
    
    except Exception as e:
        logger.error(f"删除数据库表失败: {str(e)}", exc_info=True)
        return False


async def init_sample_data():
    """初始化示例数据 (仅用于测试)"""
    logger.info("初始化示例数据...")
    
    try:
        from app.models.provider import Provider, ModelConfig
        
        async with AsyncSessionLocal() as session:
            # 检查是否已有数据
            from sqlalchemy import select
            result = await session.execute(select(Provider))
            existing = result.scalars().first()
            
            if existing:
                logger.info("数据库中已有数据,跳过初始化")
                return True
            
            # 创建示例提供商
            providers = [
                Provider(
                    name="openai-demo",
                    type="openai",
                    base_url="https://api.openai.com/v1",
                    api_key="sk-demo-key",
                    enabled=False,  # 默认禁用,需要用户配置真实密钥
                    priority=100,
                    weight=100,
                    timeout=60
                ),
                Provider(
                    name="anthropic-demo",
                    type="anthropic",
                    base_url="https://api.anthropic.com",
                    api_key="sk-ant-demo-key",
                    enabled=False,
                    priority=90,
                    weight=50,
                    timeout=60
                ),
                Provider(
                    name="gemini-demo",
                    type="gemini",
                    base_url="https://generativelanguage.googleapis.com",
                    api_key="demo-key",
                    enabled=False,
                    priority=80,
                    weight=50,
                    timeout=60
                )
            ]
            
            for provider in providers:
                session.add(provider)
            
            await session.commit()
            
            logger.info("示例数据初始化完成")
            logger.warning("注意: 示例提供商已禁用,请配置真实 API 密钥后启用")
            
            return True
    
    except Exception as e:
        logger.error(f"初始化示例数据失败: {str(e)}", exc_info=True)
        return False


async def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="数据库初始化和迁移工具")
    parser.add_argument(
        "action",
        choices=["init", "reset", "check", "sample"],
        help="操作: init=创建表, reset=重置(删除并重建), check=检查表, sample=添加示例数据"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="强制执行(用于reset操作)"
    )
    
    args = parser.parse_args()
    
    logger.info(f"数据库: {settings.database_url}")
    logger.info(f"操作: {args.action}")
    
    if args.action == "check":
        # 检查表
        tables = await check_tables_exist()
        print(f"\n数据库中的表 ({len(tables)}):")
        for table in tables:
            print(f"  - {table}")
        print()
    
    elif args.action == "init":
        # 创建表
        success = await create_tables()
        if success:
            print("\n✅ 数据库表创建成功")
            print("提示: 使用 'python scripts/init_db.py sample' 添加示例数据")
        else:
            print("\n❌ 数据库表创建失败")
            sys.exit(1)
    
    elif args.action == "reset":
        # 重置数据库
        if not args.force:
            print("\n⚠️  警告: 此操作将删除所有数据!")
            confirm = input("确认重置数据库? (输入 'yes' 确认): ")
            if confirm.lower() != "yes":
                print("操作已取消")
                return
        
        # 删除表
        await drop_tables()
        # 重新创建表
        success = await create_tables()
        
        if success:
            print("\n✅ 数据库已重置")
        else:
            print("\n❌ 数据库重置失败")
            sys.exit(1)
    
    elif args.action == "sample":
        # 添加示例数据
        # 先确保表存在
        tables = await check_tables_exist()
        if not tables:
            print("数据库表不存在,先创建表...")
            await create_tables()
        
        success = await init_sample_data()
        if success:
            print("\n✅ 示例数据已添加")
            print("注意: 示例提供商默认禁用,请配置真实 API 密钥")
        else:
            print("\n❌ 示例数据添加失败")
            sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n操作已取消")
    except Exception as e:
        logger.error(f"执行失败: {str(e)}", exc_info=True)
        sys.exit(1)