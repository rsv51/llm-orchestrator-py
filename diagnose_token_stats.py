#!/usr/bin/env python3
"""
Token 统计诊断工具
用于检查 Token 使用统计为 0 的问题
"""
import asyncio
import sys
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta

from app.models.request_log import RequestLog
from app.models.provider import Provider


async def diagnose_token_stats():
    """诊断 Token 统计问题"""
    
    # 读取数据库配置
    try:
        from app.core.config import settings
        database_url = settings.database_url
    except:
        database_url = "sqlite+aiosqlite:///./llm_orchestrator.db"
    
    print(f"🔍 连接数据库: {database_url}\n")
    
    # 创建数据库引擎
    engine = create_async_engine(database_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        # 1. 检查请求日志总数
        query = select(func.count(RequestLog.id))
        result = await session.execute(query)
        total_logs = result.scalar()
        print(f"📊 总请求日志数: {total_logs}")
        
        if total_logs == 0:
            print("❌ 没有任何请求日志!")
            print("   原因: 系统还没有处理任何请求")
            print("   解决: 请先通过 API 发送一些请求\n")
            return
        
        # 2. 检查最近 24 小时的日志
        since = datetime.utcnow() - timedelta(hours=24)
        query = select(func.count(RequestLog.id)).where(RequestLog.created_at >= since)
        result = await session.execute(query)
        recent_logs = result.scalar()
        print(f"📅 最近 24 小时日志数: {recent_logs}\n")
        
        # 3. 检查 Token 字段统计
        query = select(
            func.count(RequestLog.id).label("total"),
            func.count(RequestLog.prompt_tokens).label("has_prompt"),
            func.count(RequestLog.completion_tokens).label("has_completion"),
            func.count(RequestLog.total_tokens).label("has_total"),
            func.sum(RequestLog.prompt_tokens).label("sum_prompt"),
            func.sum(RequestLog.completion_tokens).label("sum_completion"),
            func.sum(RequestLog.total_tokens).label("sum_total")
        ).where(RequestLog.created_at >= since)
        
        result = await session.execute(query)
        stats = result.first()
        
        print("🔢 Token 字段统计 (最近 24 小时):")
        print(f"   总日志数: {stats.total}")
        print(f"   有 prompt_tokens 的: {stats.has_prompt}")
        print(f"   有 completion_tokens 的: {stats.has_completion}")
        print(f"   有 total_tokens 的: {stats.has_total}")
        print(f"   prompt_tokens 总和: {stats.sum_prompt or 0}")
        print(f"   completion_tokens 总和: {stats.sum_completion or 0}")
        print(f"   total_tokens 总和: {stats.sum_total or 0}\n")
        
        # 4. 检查最近 10 条日志的详情
        query = (
            select(RequestLog, Provider)
            .join(Provider, RequestLog.provider_id == Provider.id)
            .order_by(RequestLog.created_at.desc())
            .limit(10)
        )
        result = await session.execute(query)
        rows = result.all()
        
        print("📝 最近 10 条日志详情:")
        print("-" * 100)
        for log, provider in rows:
            print(f"时间: {log.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"提供商: {provider.name} ({provider.type})")
            print(f"模型: {log.model}")
            print(f"状态码: {log.status_code}")
            print(f"Token: prompt={log.prompt_tokens}, completion={log.completion_tokens}, total={log.total_tokens}")
            if log.error_message:
                print(f"错误: {log.error_message[:100]}")
            print("-" * 100)
        
        # 5. 分析问题
        print("\n🔍 问题分析:")
        
        if stats.total > 0 and stats.has_total == 0:
            print("❌ 所有请求的 Token 统计都是 NULL/0")
            print("\n可能原因:")
            print("1. 流式请求未添加 stream_options: {include_usage: true}")
            print("2. Provider 响应中没有 usage 字段")
            print("3. OpenAI 兼容 API 不支持返回 usage 信息")
            print("\n建议检查:")
            print("• 查看 app/providers/openai.py 第 117 行是否有 stream_options")
            print("• 查看 app/services/router.py 第 264-276 行是否正确解析 usage")
            print("• 尝试发送非流式请求测试 (stream: false)")
            print("• 检查 Provider API 是否支持返回 usage\n")
        
        elif stats.sum_total > 0:
            print("✅ Token 统计功能正常!")
            print(f"   最近 24 小时共使用 {stats.sum_total} tokens")
            print("\n如果前端仍显示 0,请检查:")
            print("• 前端是否正确调用 /api/admin/stats API")
            print("• 浏览器控制台是否有 JavaScript 错误")
            print("• 尝试刷新页面或清除浏览器缓存\n")
        
        else:
            print("⚠️ Token 统计部分缺失")
            print(f"   有 {stats.has_total}/{stats.total} 条日志包含 Token 信息")
            print("\n这可能是正常的,如果:")
            print("• 使用了不同类型的 Provider (有些不返回 usage)")
            print("• 部分请求失败 (失败的请求没有 usage)")
            print("• 使用了不同版本的 API 端点\n")


async def main():
    """主函数"""
    print("=" * 100)
    print("Token 使用统计诊断工具")
    print("=" * 100 + "\n")
    
    try:
        await diagnose_token_stats()
    except Exception as e:
        print(f"\n❌ 诊断失败: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    print("=" * 100)
    print("诊断完成")
    print("=" * 100)


if __name__ == "__main__":
    asyncio.run(main())