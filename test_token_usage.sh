#!/bin/bash

# Token 使用统计测试脚本
# 用于验证 API 是否正确返回和记录 Token 信息

echo "======================================"
echo "Token 使用统计测试"
echo "======================================"
echo ""

# 配置 (请根据实际情况修改)
API_URL="https://svcrfaowwjsn.us-west-1.clawcloudrun.com"
API_KEY="QAZ123wsx456"
MODEL_NAME="qwen3-coder-plus"

echo "📋 测试配置:"
echo "   API URL: $API_URL"
echo "   模型: $MODEL_NAME"
echo ""

# 测试 1: 非流式请求
echo "🔍 测试 1: 非流式请求 (stream: false)"
echo "--------------------------------------"

curl -X POST "$API_URL/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $API_KEY" \
  -d '{
    "model": "'"$MODEL_NAME"'",
    "messages": [
      {"role": "user", "content": "Say hello in 5 words"}
    ],
    "stream": false
  }' | jq '.'

echo ""
echo ""

# 测试 2: 流式请求
echo "🔍 测试 2: 流式请求 (stream: true)"
echo "--------------------------------------"
echo "提示: 查看最后的 usage 信息"
echo ""

curl -X POST "$API_URL/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $API_KEY" \
  -d '{
    "model": "'"$MODEL_NAME"'",
    "messages": [
      {"role": "user", "content": "Say hello in 5 words"}
    ],
    "stream": true
  }'

echo ""
echo ""

# 等待日志写入
echo "⏳ 等待 2 秒让日志写入数据库..."
sleep 2

# 测试 3: 查询统计数据
echo ""
echo "🔍 测试 3: 查询统计数据"
echo "--------------------------------------"

ADMIN_KEY="your-admin-key-here"

curl -X GET "$API_URL/api/admin/stats?hours=1" \
  -H "Authorization: Bearer $ADMIN_KEY" | jq '.'

echo ""
echo ""

# 测试 4: 查询最近日志
echo "🔍 测试 4: 查询最近日志"
echo "--------------------------------------"

curl -X GET "$API_URL/api/admin/logs?page=1&page_size=5" \
  -H "Authorization: Bearer $ADMIN_KEY" | jq '.logs[] | {
    id: .id,
    model: .model,
    provider: .provider_name,
    status: .status_code,
    prompt_tokens: .prompt_tokens,
    completion_tokens: .completion_tokens,
    total_tokens: .total_tokens,
    time: .created_at
  }'

echo ""
echo "======================================"
echo "测试完成"
echo "======================================"
echo ""
echo "📊 分析结果:"
echo ""
echo "1. 如果非流式请求返回了 usage 信息 → ✅ 基础功能正常"
echo "2. 如果流式请求最后返回了 usage chunk → ✅ 流式 usage 支持正常"
echo "3. 如果统计 API 显示 total_tokens > 0 → ✅ 统计功能正常"
echo "4. 如果日志中有 token 数据 → ✅ 日志记录正常"
echo ""
echo "如果所有 token 字段都是 0 或 null,可能的原因:"
echo "• Provider API 不支持返回 usage 信息"
echo "• Provider 配置错误(API key、base_url)"
echo "• 使用了不兼容的模型"
echo "• stream_options 未生效(需要确认 Provider 是否支持)"
echo ""