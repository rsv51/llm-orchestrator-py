#!/bin/bash

# Token 统计修复验证脚本
# 测试流式响应是否正确提取 usage 信息

BASE_URL="http://localhost:8000"
API_KEY="test-key-123"

echo "========================================="
echo "Token 统计修复验证测试"
echo "========================================="
echo ""

# 测试1: 流式请求 - 验证 usage 提取
echo "测试1: 发送流式请求并检查 Token 记录..."
echo ""

RESPONSE=$(curl -s -X POST "${BASE_URL}/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${API_KEY}" \
  -d '{
    "model": "gpt-3.5-turbo",
    "messages": [
      {"role": "user", "content": "Say hello in 5 words"}
    ],
    "stream": true,
    "temperature": 0.7
  }')

echo "流式响应已接收"
echo ""

# 等待日志写入
sleep 2

# 测试2: 检查最新日志记录
echo "测试2: 检查最新日志记录中的 Token 统计..."
echo ""

LATEST_LOG=$(curl -s "${BASE_URL}/api/v1/admin/logs?page=1&page_size=1" \
  -H "Authorization: Bearer admin123")

echo "最新日志记录:"
echo "$LATEST_LOG" | python3 -m json.tool
echo ""

# 提取 Token 信息
PROMPT_TOKENS=$(echo "$LATEST_LOG" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data['logs'][0].get('prompt_tokens', 'null') if data.get('logs') else 'null')")
COMPLETION_TOKENS=$(echo "$LATEST_LOG" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data['logs'][0].get('completion_tokens', 'null') if data.get('logs') else 'null')")
TOTAL_TOKENS=$(echo "$LATEST_LOG" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data['logs'][0].get('total_tokens', 'null') if data.get('logs') else 'null')")

echo "Token 统计结果:"
echo "  Prompt Tokens: $PROMPT_TOKENS"
echo "  Completion Tokens: $COMPLETION_TOKENS"
echo "  Total Tokens: $TOTAL_TOKENS"
echo ""

# 验证结果
if [ "$TOTAL_TOKENS" != "null" ] && [ "$TOTAL_TOKENS" != "0" ] && [ "$TOTAL_TOKENS" != "None" ]; then
    echo "✅ 成功: Token 统计已正确记录!"
    echo "   Total Tokens = $TOTAL_TOKENS (非零值)"
else
    echo "❌ 失败: Token 统计仍为 null/0"
    echo "   请检查:"
    echo "   1. Provider 是否支持返回 usage"
    echo "   2. 是否添加了 stream_options: {include_usage: true}"
    echo "   3. 日志记录逻辑是否正确执行"
fi

echo ""

# 测试3: 检查统计 API
echo "测试3: 检查统计 API 返回的 Token 总数..."
echo ""

STATS=$(curl -s "${BASE_URL}/api/v1/admin/stats" \
  -H "Authorization: Bearer admin123")

echo "统计信息:"
echo "$STATS" | python3 -m json.tool
echo ""

STATS_TOTAL=$(echo "$STATS" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('total_tokens', 'null'))")

echo "统计 API Token 总数: $STATS_TOTAL"
echo ""

if [ "$STATS_TOTAL" != "null" ] && [ "$STATS_TOTAL" != "0" ] && [ "$STATS_TOTAL" != "None" ]; then
    echo "✅ 成功: 统计 API 显示非零 Token 总数"
else
    echo "⚠️  警告: 统计 API Token 总数仍为 0"
    echo "   这可能是因为:"
    echo "   1. 历史日志缺少 Token 数据"
    echo "   2. 需要发送更多请求累积数据"
    echo "   3. 数据库查询聚合逻辑问题"
fi

echo ""
echo "========================================="
echo "测试完成"
echo "========================================="
echo ""
echo "下一步建议:"
echo "1. 如果 Token 仍为 0,运行诊断脚本:"
echo "   python diagnose_token_stats.py"
echo ""
echo "2. 检查 Provider 日志确认是否返回 usage:"
echo "   tail -f logs/app.log | grep usage"
echo ""
echo "3. 尝试使用不同的 Provider 或模型测试"