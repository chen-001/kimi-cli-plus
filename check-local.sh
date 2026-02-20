#!/bin/bash
# 本地检查脚本 - 在推送前运行，确保 CI 通过

set -e

echo "=========================================="
echo "🚀 本地检查开始"
echo "=========================================="
echo ""

echo "📋 Step 1: 代码规范检查 (ruff)"
echo "------------------------------------------"
uv run ruff check
uv run ruff format --check
echo "✅ 代码规范检查通过"
echo ""

echo "📋 Step 2: 类型检查 (已跳过)"
echo "------------------------------------------"
echo "⏭️  pyright 已禁用 - 插件系统的动态特性不适合静态类型检查"
echo ""

echo "📋 Step 3: 单元测试 (pytest tests)"
echo "------------------------------------------"
uv run pytest tests -v --tb=short
echo "✅ 单元测试通过"
echo ""

echo "=========================================="
echo "🎉 所有本地检查通过！可以安全推送了"
echo "=========================================="
echo ""
echo "推送命令: git push origin main"
