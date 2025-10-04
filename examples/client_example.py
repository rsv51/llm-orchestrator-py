"""
LLM Orchestrator 客户端使用示例

展示如何使用 Python 客户端调用 API
"""
import asyncio
import httpx
from typing import AsyncGenerator


class LLMOrchestratorClient:
    """LLM Orchestrator 客户端"""
    
    def __init__(self, base_url: str = "http://localhost:8000", api_key: str = ""):
        """
        初始化客户端
        
        Args:
            base_url: API 基础 URL
            api_key: API 密钥
        """
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
    
    async def list_models(self):
        """获取可用模型列表"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/v1/models",
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()
    
    async def chat_completion(
        self,
        messages: list,
        model: str = "gpt-3.5-turbo",
        stream: bool = False,
        **kwargs
    ):
        """
        发送聊天完成请求
        
        Args:
            messages: 消息列表
            model: 模型名称
            stream: 是否使用流式响应
            **kwargs: 其他参数(temperature, max_tokens等)
        """
        data = {
            "model": model,
            "messages": messages,
            "stream": stream,
            **kwargs
        }
        
        if stream:
            return self._stream_chat_completion(data)
        else:
            return await self._chat_completion(data)
    
    async def _chat_completion(self, data: dict):
        """非流式聊天完成"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/v1/chat/completions",
                headers=self.headers,
                json=data
            )
            response.raise_for_status()
            return response.json()
    
    async def _stream_chat_completion(self, data: dict) -> AsyncGenerator[str, None]:
        """流式聊天完成"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/v1/chat/completions",
                headers=self.headers,
                json=data
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        chunk = line[6:]
                        if chunk.strip() == "[DONE]":
                            break
                        yield chunk


async def example_basic_chat():
    """示例1: 基本聊天"""
    print("=== 示例1: 基本聊天 ===\n")
    
    client = LLMOrchestratorClient(
        base_url="http://localhost:8000",
        api_key="test-key"
    )
    
    response = await client.chat_completion(
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello! Can you introduce yourself?"}
        ],
        model="gpt-3.5-turbo",
        max_tokens=100
    )
    
    print(f"模型: {response['model']}")
    print(f"提供商: {response.get('provider', 'unknown')}")
    print(f"回复: {response['choices'][0]['message']['content']}")
    print(f"Token 使用: {response['usage']}")
    print()


async def example_streaming_chat():
    """示例2: 流式聊天"""
    print("=== 示例2: 流式聊天 ===\n")
    
    client = LLMOrchestratorClient(
        base_url="http://localhost:8000",
        api_key="test-key"
    )
    
    print("AI: ", end="", flush=True)
    
    stream = await client.chat_completion(
        messages=[
            {"role": "user", "content": "Count from 1 to 10 slowly."}
        ],
        model="gpt-3.5-turbo",
        stream=True
    )
    
    import json
    async for chunk in stream:
        try:
            data = json.loads(chunk)
            if data['choices'][0]['delta'].get('content'):
                print(data['choices'][0]['delta']['content'], end="", flush=True)
        except json.JSONDecodeError:
            continue
    
    print("\n")


async def example_multi_turn_conversation():
    """示例3: 多轮对话"""
    print("=== 示例3: 多轮对话 ===\n")
    
    client = LLMOrchestratorClient(
        base_url="http://localhost:8000",
        api_key="test-key"
    )
    
    messages = [
        {"role": "system", "content": "You are a helpful math tutor."}
    ]
    
    # 第一轮
    messages.append({"role": "user", "content": "What is 15 + 27?"})
    response = await client.chat_completion(messages=messages, max_tokens=50)
    assistant_reply = response['choices'][0]['message']['content']
    messages.append({"role": "assistant", "content": assistant_reply})
    print(f"用户: What is 15 + 27?")
    print(f"AI: {assistant_reply}\n")
    
    # 第二轮
    messages.append({"role": "user", "content": "Now multiply that by 3"})
    response = await client.chat_completion(messages=messages, max_tokens=50)
    assistant_reply = response['choices'][0]['message']['content']
    print(f"用户: Now multiply that by 3")
    print(f"AI: {assistant_reply}\n")


async def example_list_models():
    """示例4: 列出可用模型"""
    print("=== 示例4: 列出可用模型 ===\n")
    
    client = LLMOrchestratorClient(
        base_url="http://localhost:8000",
        api_key="test-key"
    )
    
    models = await client.list_models()
    
    print(f"总共 {len(models['data'])} 个模型:")
    for model in models['data'][:10]:
        print(f"  - {model['id']}")
    
    if len(models['data']) > 10:
        print(f"  ... 还有 {len(models['data']) - 10} 个模型")
    print()


async def example_custom_parameters():
    """示例5: 自定义参数"""
    print("=== 示例5: 自定义参数 ===\n")
    
    client = LLMOrchestratorClient(
        base_url="http://localhost:8000",
        api_key="test-key"
    )
    
    response = await client.chat_completion(
        messages=[
            {"role": "user", "content": "Write a creative story beginning."}
        ],
        model="gpt-3.5-turbo",
        temperature=1.2,  # 更高的创造性
        max_tokens=150,
        top_p=0.9,
        presence_penalty=0.6
    )
    
    print(f"创造性故事开头:")
    print(response['choices'][0]['message']['content'])
    print()


async def main():
    """运行所有示例"""
    print("=" * 60)
    print("LLM Orchestrator 客户端使用示例")
    print("=" * 60)
    print()
    
    try:
        # 示例1: 基本聊天
        await example_basic_chat()
        
        # 示例2: 流式聊天
        await example_streaming_chat()
        
        # 示例3: 多轮对话
        await example_multi_turn_conversation()
        
        # 示例4: 列出模型
        await example_list_models()
        
        # 示例5: 自定义参数
        await example_custom_parameters()
        
        print("=" * 60)
        print("所有示例运行完成!")
        print("=" * 60)
        
    except httpx.HTTPError as e:
        print(f"\n错误: 无法连接到 API")
        print(f"请确保服务正在运行: http://localhost:8000")
        print(f"详细信息: {e}")
    except Exception as e:
        print(f"\n发生错误: {e}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n已取消")