#!/usr/bin/env bash
set -euo pipefail

# kimi-cli-plus 一键安装脚本
# 用法: curl -LsSf https://raw.githubusercontent.com/chen-001/kimi-cli-plus/main/scripts/install.sh | bash

PACKAGE_NAME="kimi-cli-plus"
PYTHON_VERSION="3.13"

install_uv() {
  echo "Installing uv (Python package manager)..."
  if command -v curl >/dev/null 2>&1; then
    curl -fsSL https://astral.sh/uv/install.sh | sh
    return
  fi

  if command -v wget >/dev/null 2>&1; then
    wget -qO- https://astral.sh/uv/install.sh | sh
    return
  fi

  echo "Error: curl or wget is required to install uv." >&2
  exit 1
}

# 检查 uv 是否已安装
if command -v uv >/dev/null 2>&1; then
  UV_BIN="uv"
else
  install_uv
  # 重新加载 shell 配置以获取 uv 命令
  if [ -f "$HOME/.local/bin/env" ]; then
    . "$HOME/.local/bin/env"
  elif [ -f "$HOME/.cargo/env" ]; then
    . "$HOME/.cargo/env"
  fi
  UV_BIN="uv"
fi

if ! command -v "$UV_BIN" >/dev/null 2>&1; then
  echo "Error: uv not found after installation. Please restart your shell and try again." >&2
  exit 1
fi

echo "Installing $PACKAGE_NAME..."
"$UV_BIN" tool install --python "$PYTHON_VERSION" "$PACKAGE_NAME"

echo ""
echo "✅ $PACKAGE_NAME installed successfully!"
echo ""
echo "Available commands:"
echo "  kcp           - Quick command"
echo "  kimi-plus     - Full command"
echo "  kimi-cli-plus - Alternative command"
echo ""
echo "To verify installation, run: kcp --version"
echo ""
echo "To upgrade: uv tool upgrade $PACKAGE_NAME --no-cache"
echo "To uninstall: uv tool uninstall $PACKAGE_NAME"
