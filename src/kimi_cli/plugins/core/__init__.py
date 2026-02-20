"""插件核心基础设施。"""

from .patch_base import PatchBase, patch_class, safe_patch_method

__all__ = ["PatchBase", "safe_patch_method", "patch_class"]
