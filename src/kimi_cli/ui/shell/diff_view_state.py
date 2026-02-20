"""
Diff view 运行时状态管理模块。

提供全局的 diff view 启用/禁用状态，允许用户通过快捷键实时切换。
"""

from __future__ import annotations

# 运行时 diff view 状态
# None 表示使用配置值，True/False 表示强制启用/禁用
_diff_view_runtime_state: bool | None = None


def is_diff_view_enabled() -> bool:
    """
    检查 diff view 是否启用。
    
    优先使用运行时状态，如果未设置则读取配置文件。
    """
    global _diff_view_runtime_state
    
    # 如果运行时状态已设置，直接使用
    if _diff_view_runtime_state is not None:
        return _diff_view_runtime_state
    
    # 否则从配置读取
    try:
        from kimi_cli.config import load_config
        config = load_config()
        plugin_config = getattr(config, 'plugin_config', None)
        if plugin_config is None:
            return True
        return getattr(plugin_config, 'enable_diff_view', True)
    except Exception:
        # 默认启用
        return True


def toggle_diff_view() -> bool:
    """
    切换 diff view 的启用状态。
    
    Returns:
        切换后的新状态（True=启用，False=禁用）
    """
    global _diff_view_runtime_state
    
    # 获取当前状态
    current = is_diff_view_enabled()
    
    # 切换到相反状态
    _diff_view_runtime_state = not current
    
    return _diff_view_runtime_state


def get_diff_view_status() -> tuple[bool, bool]:
    """
    获取 diff view 的完整状态信息。
    
    Returns:
        (是否启用, 是否使用运行时覆盖) 的元组
    """
    global _diff_view_runtime_state
    
    if _diff_view_runtime_state is not None:
        return (_diff_view_runtime_state, True)
    
    return (is_diff_view_enabled(), False)


def reset_runtime_state() -> None:
    """重置运行时状态，恢复使用配置值。"""
    global _diff_view_runtime_state
    _diff_view_runtime_state = None
