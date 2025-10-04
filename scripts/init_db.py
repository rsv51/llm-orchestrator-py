"""
数据库初始化脚本 - 简化版
仅用于检查数据库状态,实际表创建由 Alembic 完成
"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import inspect, text
from app.core.database import engine, AsyncSessionLocal
from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger(__name__)


async def check_tables_exist():
    """检查数据库表是否存在"""
    async with engine.begin() as conn:
        def _check(connection):
            inspector = inspect(connection)
            return inspector.get_table_names()
        
        tables = await conn.run_sync(_check)
        return tables


async def verify_database():
    """验证数据库连接和表结构"""
    try:
        logger.info("检查数据库连接...")
        
        # 测试连接
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        
        logger.info("✅ 数据库连接正常")
        
        # 检查表
        tables = await check_tables_exist()
        expected_tables = [
            'providers', 'models', 'model_providers',
            'request_logs', 'provider_health', 'provider_stats'
        ]
        
        missing_tables = [t for t in expected_tables if t not in tables]
        
        if missing_tables:
            logger.warning(f"缺少表: {missing_tables}")
            logger.info("请运行: alembic upgrade head")
            return False
        
        logger.info(f"✅ 所有必需的表都存在 ({len(tables)} 个表)")
        return True
        
    except Exception as e:
        logger.error(f"数据库验证失败: {str(e)}", exc_info=True)
        return False


async def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="数据库初始化工具")
    parser.add_argument(
        "action",
        choices=["init", "check"],
        help="操作: init=验证数据库(推荐用 alembic upgrade head), check=检查表状态"
    )
    
    args = parser.parse_args()
    
    logger.info(f"数据库: {settings.database_url}")
    
    if args.action == "check":
        # 检查表
        tables = await check_tables_exist()
        print(f"\n数据库中的表 ({len(tables)}):")
        for table in sorted(tables):
            print(f"  - {table}")
        print()
    
    elif args.action == "init":
        # 验证数据库
        success = await verify_database()
        if success:
            print("\n✅ 数据库状态正常")
        else:
            print("\n⚠️ 数据库需要初始化")
            print("运行: alembic upgrade head")
            sys.exit(1)
    
    await engine.dispose()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n操作已取消")
    except Exception as e:
        logger.error(f"执行失败: {str(e)}", exc_info=True)
        sys.exit(1)