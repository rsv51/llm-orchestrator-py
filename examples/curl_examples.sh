#!/bin/bash

# LLM Orchestrator API cURL 使用示例
# 展示如何使用 cURL 命令调用各个 API 端点

BASE_URL="http://localhost:8000"
API_KEY="test-key"
ADMIN_KEY="admin-key"

echo "================================"
echo "LLM Orchestrator cURL 示例"
echo "================================"
echo ""

# 示例1: 健康检查
echo "=== 示例1: 健康检查 ==="
curl -X GET "${BASE_URL}/health"
echo -e "\n"

# 示例2: 获取模型列表
echo "=== 示例2: 获取模型列表 ==="
curl -X GET "${BASE_URL}/v1/models" \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "Content-Type: application/json"
echo -e "\n"

# 示例3: 基本聊天完成
echo "=== 示例3: 基本聊天完成 ==="
curl -X POST "${BASE_URL}/v1/chat/completions" \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-3.5-turbo",
    "messages": [
      {"role": "user", "content": "Hello! Say hi back in one sentence."}
    ],
    "max_tokens": 50
  }'
echo -e "\n"

# 示例4: 流式聊天完成
echo "=== 示例4: 流式聊天完成 ==="
curl -X POST "${BASE_URL}/v1/chat/completions" \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "Content-Type: application/json" \
  -N \
  -d '{
    "model": "gpt-3.5-turbo",
    "messages": [
      {"role": "user", "content": "Count from 1 to 5"}
    ],
    "stream": true,
    "max_tokens": 50
  }'
echo -e "\n"

# 示例5: 带自定义参数的聊天
echo "=== 示例5: 带自定义参数的聊天 ==="
curl -X POST "${BASE_URL}/v1/chat/completions" \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-3.5-turbo",
    "messages": [
      {"role": "system", "content": "You are a helpful assistant."},
      {"role": "user", "content": "Tell me a short joke"}
    ],
    "temperature": 0.8,
    "max_tokens": 100,
    "top_p": 0.9
  }'
echo -e "\n"

# 示例6: 获取提供商列表 (管理员)
echo "=== 示例6: 获取提供商列表 ==="
curl -X GET "${BASE_URL}/admin/providers" \
  -H "Authorization: Bearer ${ADMIN_KEY}" \
  -H "Content-Type: application/json"
echo -e "\n"

# 示例7: 获取系统健康状态 (管理员)
echo "=== 示例7: 获取系统健康状态 ==="
curl -X GET "${BASE_URL}/admin/health" \
  -H "Authorization: Bearer ${ADMIN_KEY}" \
  -H "Content-Type: application/json"
echo -e "\n"

# 示例8: 添加新提供商 (管理员)
echo "=== 示例8: 添加新提供商 ==="
curl -X POST "${BASE_URL}/admin/providers" \
  -H "Authorization: Bearer ${ADMIN_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "my-openai",
    "type": "openai",
    "api_key": "sk-xxx",
    "base_url": "https://api.openai.com/v1",
    "priority": 100,
    "enabled": true
  }'
echo -e "\n"

# 示例9: 更新提供商 (管理员)
echo "=== 示例9: 更新提供商 (将 provider_id 替换为实际ID) ==="
echo "curl -X PUT '${BASE_URL}/admin/providers/1' \\"
echo "  -H 'Authorization: Bearer ${ADMIN_KEY}' \\"
echo "  -H 'Content-Type: application/json' \\"
echo "  -d '{\"enabled\": false}'"
echo -e "\n"

# 示例10: 删除提供商 (管理员)
echo "=== 示例10: 删除提供商 (将 provider_id 替换为实际ID) ==="
echo "curl -X DELETE '${BASE_URL}/admin/providers/1' \\"
echo "  -H 'Authorization: Bearer ${ADMIN_KEY}'"
echo -e "\n"

# 示例11: 获取请求统计 (管理员)
echo "=== 示例11: 获取请求统计 ==="
curl -X GET "${BASE_URL}/admin/stats?hours=24" \
  -H "Authorization: Bearer ${ADMIN_KEY}" \
  -H "Content-Type: application/json"
echo -e "\n"

echo "================================"
echo "所有示例完成!"
echo "================================"