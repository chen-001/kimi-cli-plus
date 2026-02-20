"""
版本兼容性检查
==============

检查插件与当前kimi-cli版本的兼容性。
"""

from __future__ import annotations

import warnings


def get_kimi_version() -> str | None:
    """获取当前kimi-cli版本。"""
    try:
        from kimi_cli.constant import VERSION

        return VERSION
    except Exception:
        # 如果无法获取（如未安装），返回默认值
        return "0.70.0"


def parse_version(version_str: str) -> tuple[int, ...]:
    """解析版本字符串为元组。"""
    parts = version_str.split(".")
    result = []
    for part in parts:
        # 只取数字部分
        num = ""
        for char in part:
            if char.isdigit():
                num += char
            else:
                break
        if num:
            result.append(int(num))
    return tuple(result)


def check_compatibility(
    plugin_version: str, min_kimi_version: str, max_kimi_version: str | None = None
) -> tuple[bool, str]:
    """
    检查插件与kimi-cli的兼容性。

    Returns:
        (is_compatible, message)
    """
    kimi_version = get_kimi_version()

    if kimi_version is None:
        return False, "无法检测kimi-cli版本"

    kimi_tuple = parse_version(kimi_version)
    min_tuple = parse_version(min_kimi_version)

    if kimi_tuple < min_tuple:
        return False, f"kimi-cli版本过低。需要 >= {min_kimi_version}，当前 {kimi_version}"

    if max_kimi_version:
        max_tuple = parse_version(max_kimi_version)
        if kimi_tuple > max_tuple:
            return False, f"kimi-cli版本过高。插件可能不兼容当前版本 {kimi_version}"

    return True, f"版本兼容 (kimi-cli {kimi_version}, 插件 {plugin_version})"


def warn_if_incompatible():
    """如果不兼容，发出警告。"""
    from kimi_cli.plugins import MIN_KIMI_VERSION, PLUGIN_VERSION

    is_ok, msg = check_compatibility(PLUGIN_VERSION, MIN_KIMI_VERSION)

    if not is_ok:
        warnings.warn(f"[Kimi Plugins] {msg}", RuntimeWarning, stacklevel=2)
    else:
        # 调试信息
        import logging

        logger = logging.getLogger(__name__)
        logger.debug(msg)
