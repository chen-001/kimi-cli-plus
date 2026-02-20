"""
Kimi CLI 用户插件系统
=====================

这个目录包含用户自定义的可插拔功能，不影响官方代码，可以随官方更新而保留。
"""

from __future__ import annotations

import logging
import warnings

logger = logging.getLogger(__name__)

PLUGIN_VERSION = "1.0.0"
MIN_KIMI_VERSION = "0.70.0"

_applied_patches: list[str] = []


def apply_all_patches():
    """应用所有插件补丁。"""
    global _applied_patches

    if _applied_patches:
        return

    print(f"[Plugin] Loading user plugins v{PLUGIN_VERSION}...")

    # 导入并应用各个补丁模块
    # 注意：从模块导入，不是从函数导入
    try:
        from kimi_cli.plugins.patches import visualize_patch as viz_module

        if hasattr(viz_module, "patch") and callable(viz_module.patch) and viz_module.patch():
            _applied_patches.append("visualize")
            print("[Plugin] ✓ visualize patch applied")
    except Exception as e:
        warnings.warn(f"[Plugin] visualize patch failed: {e}", RuntimeWarning, stacklevel=2)

    try:
        from kimi_cli.plugins.patches import kimisoul_patch as ks_module

        if hasattr(ks_module, "patch") and callable(ks_module.patch) and ks_module.patch():
            _applied_patches.append("kimisoul")
            print("[Plugin] ✓ kimisoul patch applied")
    except Exception as e:
        warnings.warn(f"[Plugin] kimisoul patch failed: {e}", RuntimeWarning, stacklevel=2)

    try:
        from kimi_cli.plugins.patches import mod_tracker_patch as mt_module

        if hasattr(mt_module, "patch") and callable(mt_module.patch) and mt_module.patch():
            _applied_patches.append("mod_tracker")
            print("[Plugin] ✓ mod_tracker patch applied")
    except Exception as e:
        warnings.warn(f"[Plugin] mod_tracker patch failed: {e}", RuntimeWarning, stacklevel=2)

    # NOTE: approval_patch disabled - using standard approval system instead
    # The standard approval.py now supports INQUIRY_ACTIONS for AskUser tool
    # try:
    #     from kimi_cli.plugins.patches import approval_patch as ap_module
    #     if hasattr(ap_module, 'patch') and callable(ap_module.patch):
    #         if ap_module.patch():
    #             _applied_patches.append("approval")
    #             print("[Plugin] ✓ approval patch applied")
    # except Exception as e:
    #     warnings.warn(f"[Plugin] approval patch failed: {e}", RuntimeWarning)

    # NOTE: askuser_tool_patch disabled - AskUser tool is now loaded via agent.yaml
    # try:
    #     # 功能2补充: 自动注册 AskUser 工具
    #     from kimi_cli.plugins.patches import askuser_tool_patch as aut_module
    #     if hasattr(aut_module, 'patch') and callable(aut_module.patch):
    #         if aut_module.patch():
    #             _applied_patches.append("askuser_tool")
    #             print("[Plugin] ✓ askuser tool patch applied")
    # except Exception as e:
    #     warnings.warn(f"[Plugin] askuser tool patch failed: {e}", RuntimeWarning)

    if _applied_patches:
        print(f"[Plugin] All patches applied: {_applied_patches}")
    else:
        print("[Plugin] Warning: No patches were applied")


def get_applied_patches() -> list[str]:
    """获取已应用的补丁列表。"""
    return _applied_patches.copy()


__all__ = ["apply_all_patches", "get_applied_patches", "PLUGIN_VERSION"]
