#!/usr/bin/env python
"""
Kimi CLI 插件入口
=================

带插件支持的kimi-cli启动入口。

使用方法：
    python -m kimi_cli.plugins.entry [arguments...]

或者设置别名：
    alias km='/Users/chenzongwei/kimi-cli/kimi-with-plugins'
"""

from __future__ import annotations

import sys
import warnings

# 在导入任何kimi_cli模块之前，先应用补丁
# 这是关键：补丁必须在原始模块被导入之前应用
try:
    from kimi_cli.plugins import apply_all_patches

    apply_all_patches()
except Exception as e:
    warnings.warn(
        f"[Kimi Plugins] 加载插件失败: {e}\n将继续启动kimi-cli，但插件功能不可用。",
        RuntimeWarning,
        stacklevel=2,
    )

# 现在导入并启动原版kimi-cli
from kimi_cli.cli import cli


def main():
    """主入口函数。"""
    return cli()


if __name__ == "__main__":
    sys.exit(main())
