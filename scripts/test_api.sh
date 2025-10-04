#!/bin/bash

# API 测试工具启动脚本 (Linux/macOS)

echo "================================"
echo "LLM Orchestrator API 测试工具"
echo "================================"
echo ""

# 检查虚拟环境
if [ -d "../venv" ]; then
    source ../venv/bin/activate
    echo "已激活虚拟环境"
else
    echo "警告: 未找到虚拟环境，使用系统 Python"
fi

echo ""
echo "运行测试..."
echo ""

python test_api.py "$@"