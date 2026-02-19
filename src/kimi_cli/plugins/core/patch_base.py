"""
安全的Monkey Patch基础设施
==========================

提供可回滚、可追踪的方法替换机制。
"""

from __future__ import annotations

import functools
import inspect
from typing import Any, Callable, TypeVar

T = TypeVar("T")

# 存储原始方法的备份
_original_methods: dict[tuple[type, str], Callable] = {}

def safe_patch_method(cls: type, method_name: str) -> Callable:
    """
    装饰器：安全地替换类的方法，保留原始方法。
    
    使用示例：
        @safe_patch_method(KimiSoul, '_turn')
        async def patched_turn(original, self, user_message):
            # original 是原始方法
            result = await original(self, user_message)
            return result
    """
    def decorator(new_method: Callable) -> Callable:
        # 获取原始方法
        original_method = getattr(cls, method_name, None)
        
        if original_method is None:
            raise AttributeError(f"{cls.__name__} has no method '{method_name}'")
        
        # 保存原始方法
        key = (cls, method_name)
        _original_methods[key] = original_method
        
        # 检查是否是异步方法
        is_async = inspect.iscoroutinefunction(original_method)
        
        if is_async:
            @functools.wraps(original_method)
            async def wrapper(self, *args, **kwargs):
                return await new_method(original_method, self, *args, **kwargs)
        else:
            @functools.wraps(original_method)
            def wrapper(self, *args, **kwargs):
                return new_method(original_method, self, *args, **kwargs)
        
        # 替换方法
        setattr(cls, method_name, wrapper)
        
        return wrapper
    
    return decorator

def patch_class(cls: type) -> Callable:
    """
    装饰器：标记一个类为补丁类，其apply方法会在导入时执行。
    
    使用示例：
        @patch_class
        class MyPatch:
            def apply(self):
                # 应用补丁
                pass
    """
    def decorator(patch_cls: T) -> T:
        # 创建实例并应用补丁
        instance = patch_cls()
        if hasattr(instance, 'apply') and callable(instance.apply):
            instance.apply()
        return patch_cls
    return decorator

class PatchBase:
    """
    补丁基类，提供标准的补丁应用和回滚机制。
    
    子类需要实现：
    - apply(): 应用补丁
    - get_patch_name(): 返回补丁名称
    """
    
    _applied = False
    _backups: dict[str, Any] = {}
    
    def apply(self) -> bool:
        """应用补丁，子类应重写此方法。"""
        raise NotImplementedError
    
    def get_patch_name(self) -> str:
        """返回补丁名称。"""
        return self.__class__.__name__
    
    def is_applied(self) -> bool:
        """检查补丁是否已应用。"""
        return self._applied
    
    def _backup_method(self, cls: type, method_name: str) -> Callable:
        """备份类的方法。"""
        original = getattr(cls, method_name)
        key = f"{cls.__name__}.{method_name}"
        self._backups[key] = original
        return original
    
    def _restore_method(self, cls: type, method_name: str) -> bool:
        """恢复类的方法到原始状态。"""
        key = f"{cls.__name__}.{method_name}"
        if key in self._backups:
            setattr(cls, method_name, self._backups[key])
            del self._backups[key]
            return True
        return False

def wrap_method(cls: type, method_name: str, wrapper_factory: Callable) -> None:
    """
    通用方法包装器。
    
    Args:
        cls: 要修改的类
        method_name: 方法名
        wrapper_factory: 接收原始方法，返回新方法的工厂函数
    """
    original = getattr(cls, method_name)
    new_method = wrapper_factory(original)
    functools.update_wrapper(new_method, original)
    setattr(cls, method_name, new_method)
