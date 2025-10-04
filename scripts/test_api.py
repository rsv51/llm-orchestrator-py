"""
API 测试工具

用于测试 LLM Orchestrator API 的各个端点
"""
import asyncio
import sys
from pathlib import Path
import json

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import httpx
from typing import Optional


class APITester:
    """API 测试类"""
    
    def __init__(self, base_url: str = "http://localhost:8000", api_key: Optional[str] = None, admin_key: Optional[str] = None):
        self.base_url = base_url
        self.api_key = api_key or "test-key"
        self.admin_key = admin_key or "admin-key"
    
    def _get_headers(self, use_admin: bool = False):
        """获取请求头"""
        key = self.admin_key if use_admin else self.api_key
        return {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json"
        }
    
    async def test_health(self):
        """测试健康检查端点"""
        print("\n=== 测试健康检查 ===")
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.base_url}/health")
                print(f"状态码: {response.status_code}")
                print(f"响应: {response.json()}")
                return response.status_code == 200
        except Exception as e:
            print(f"错误: {e}")
            return False
    
    async def test_models_list(self):
        """测试模型列表端点"""
        print("\n=== 测试模型列表 ===")
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/v1/models",
                    headers=self._get_headers()
                )
                print(f"状态码: {response.status_code}")
                data = response.json()
                print(f"模型数量: {len(data.get('data', []))}")
                for model in data.get('data', [])[:5]:
                    print(f"  - {model['id']}")
                return response.status_code == 200
        except Exception as e:
            print(f"错误: {e}")
            return False
    
    async def test_chat_completion(self):
        """测试聊天完成端点"""
        print("\n=== 测试聊天完成 ===")
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                request_data = {
                    "model": "gpt-3.5-turbo",
                    "messages": [
                        {"role": "user", "content": "Say 'Hello, World!' in one sentence."}
                    ],
                    "max_tokens": 50
                }
                
                print(f"发送请求: {json.dumps(request_data, indent=2)}")
                
                response = await client.post(
                    f"{self.base_url}/v1/chat/completions",
                    headers=self._get_headers(),
                    json=request_data
                )
                
                print(f"状态码: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    print(f"响应内容: {data['choices'][0]['message']['content']}")
                    print(f"使用的提供商: {data.get('provider', 'unknown')}")
                    print(f"Token 使用: {data.get('usage', {})}")
                else:
                    print(f"错误响应: {response.text}")
                
                return response.status_code == 200
        except Exception as e:
            print(f"错误: {e}")
            return False
    
    async def test_providers_list(self):
        """测试提供商列表端点"""
        print("\n=== 测试提供商列表 ===")
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/admin/providers",
                    headers=self._get_headers(use_admin=True)
                )
                print(f"状态码: {response.status_code}")
                
                if response.status_code == 200:
                    providers = response.json()
                    print(f"提供商数量: {len(providers)}")
                    for provider in providers:
                        status = "✓ 启用" if provider['enabled'] else "✗ 禁用"
                        print(f"  - {provider['name']} ({provider['type']}) {status}")
                else:
                    print(f"错误响应: {response.text}")
                
                return response.status_code == 200
        except Exception as e:
            print(f"错误: {e}")
            return False
    
    async def test_system_health(self):
        """测试系统健康状态端点"""
        print("\n=== 测试系统健康状态 ===")
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/admin/health",
                    headers=self._get_headers(use_admin=True)
                )
                print(f"状态码: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    print(f"系统状态: {data['status']}")
                    print(f"数据库状态: {data['database_status']}")
                    print(f"缓存状态: {data['cache_status']}")
                    print(f"提供商健康:")
                    for provider in data['providers']:
                        status = "✓ 健康" if provider['is_healthy'] else "✗ 不健康"
                        print(f"  - {provider['provider_name']}: {status}")
                else:
                    print(f"错误响应: {response.text}")
                
                return response.status_code == 200
        except Exception as e:
            print(f"错误: {e}")
            return False
    
    async def run_all_tests(self):
        """运行所有测试"""
        print("=" * 50)
        print("LLM Orchestrator API 测试工具")
        print("=" * 50)
        print(f"基础URL: {self.base_url}")
        
        tests = [
            ("健康检查", self.test_health),
            ("模型列表", self.test_models_list),
            ("聊天完成", self.test_chat_completion),
            ("提供商列表", self.test_providers_list),
            ("系统健康", self.test_system_health),
        ]
        
        results = {}
        for name, test_func in tests:
            try:
                results[name] = await test_func()
            except Exception as e:
                print(f"\n测试 {name} 时发生异常: {e}")
                results[name] = False
        
        # 打印总结
        print("\n" + "=" * 50)
        print("测试总结")
        print("=" * 50)
        
        passed = sum(1 for v in results.values() if v)
        total = len(results)
        
        for name, result in results.items():
            status = "✓ 通过" if result else "✗ 失败"
            print(f"{name}: {status}")
        
        print(f"\n总计: {passed}/{total} 通过")
        
        return passed == total


async def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="LLM Orchestrator API 测试工具")
    parser.add_argument(
        "--url",
        default="http://localhost:8000",
        help="API 基础 URL (默认: http://localhost:8000)"
    )
    parser.add_argument(
        "--api-key",
        default="test-key",
        help="API 密钥 (默认: test-key)"
    )
    parser.add_argument(
        "--admin-key",
        default="admin-key",
        help="管理员密钥 (默认: admin-key)"
    )
    parser.add_argument(
        "--test",
        choices=["health", "models", "chat", "providers", "system", "all"],
        default="all",
        help="要运行的测试 (默认: all)"
    )
    
    args = parser.parse_args()
    
    tester = APITester(
        base_url=args.url,
        api_key=args.api_key,
        admin_key=args.admin_key
    )
    
    if args.test == "all":
        success = await tester.run_all_tests()
    else:
        test_map = {
            "health": tester.test_health,
            "models": tester.test_models_list,
            "chat": tester.test_chat_completion,
            "providers": tester.test_providers_list,
            "system": tester.test_system_health,
        }
        success = await test_map[args.test]()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n测试已取消")
    except Exception as e:
        print(f"\n执行失败: {e}")
        sys.exit(1)