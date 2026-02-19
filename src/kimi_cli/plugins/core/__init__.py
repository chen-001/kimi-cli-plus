"""插件核心基础设施。"""

from .patch_base import PatchBase, safe_patch_method, patch_class

__all__ = ["PatchBase", "safe_patch_method", "patch_class"]
