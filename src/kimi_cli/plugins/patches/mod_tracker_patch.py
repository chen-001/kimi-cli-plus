"""
功能4: 修改状态栏 Patch
=======================

在底部状态栏显示整个session累积的代码修改情况：
- 各文件增删行数
- 总增删行数
- 修改文件数
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from kimi_cli.plugins.core import PatchBase
from kimi_cli.plugins.patches.kimisoul_patch import KimiSoulPatch


@dataclass
class FileChange:
    """单个文件的修改记录。"""
    path: str
    lines_added: int = 0
    lines_removed: int = 0
    edit_count: int = 0
    
    @property
    def net_change(self) -> int:
        """净变更行数。"""
        return self.lines_added - self.lines_removed


@dataclass
class SessionModifications:
    """整个session的修改追踪。"""
    file_changes: dict[str, FileChange] = field(default_factory=dict)
    
    def record_change(self, path: str, old_text: str, new_text: str) -> None:
        """记录一次文件修改。"""
        old_lines = old_text.splitlines()
        new_lines = new_text.splitlines()
        
        added = len([l for l in new_lines if l])
        removed = len([l for l in old_lines if l])
        
        if path not in self.file_changes:
            self.file_changes[path] = FileChange(path=path)
        
        change = self.file_changes[path]
        change.lines_added += max(0, len(new_lines) - len(old_lines))
        change.lines_removed += max(0, len(old_lines) - len(new_lines))
        change.edit_count += 1
        
        # 同时更新Turn统计
        KimiSoulPatch.record_code_change(
            lines_added=max(0, len(new_lines) - len(old_lines)),
            lines_removed=max(0, len(old_lines) - len(new_lines))
        )
    
    @property
    def total_added(self) -> int:
        """总共增加行数。"""
        return sum(c.lines_added for c in self.file_changes.values())
    
    @property
    def total_removed(self) -> int:
        """总共删除行数。"""
        return sum(c.lines_removed for c in self.file_changes.values())
    
    @property
    def total_files(self) -> int:
        """修改的文件数。"""
        return len(self.file_changes)
    
    def format_summary(self) -> str:
        """格式化为简短摘要。"""
        if not self.file_changes:
            return ""
        return f"+{self.total_added}/-{self.total_removed} ({self.total_files} files)"


# 全局修改追踪器
_mod_tracker = SessionModifications()


def get_mod_tracker() -> SessionModifications:
    """获取全局修改追踪器。"""
    return _mod_tracker


class ModTrackerPatch(PatchBase):
    """修改追踪器的补丁。"""
    
    def get_patch_name(self) -> str:
        return "mod_tracker"
    
    def apply(self) -> bool:
        """应用补丁。"""
        try:
            self._patch_file_tools()
            self._patch_status_snapshot()
            self._patch_prompt_render()
            print(f"[Plugin] {self.get_patch_name()} applied successfully")
            return True
        except Exception as e:
            print(f"[Plugin] Failed to apply {self.get_patch_name()}: {e}")
            return False
    
    def _patch_file_tools(self) -> None:
        """Hook文件修改工具。"""
        from kimi_cli.tools.file.write import WriteFile
        from kimi_cli.tools.file.replace import StrReplaceFile
        
        # Hook WriteFile
        original_write_call = WriteFile.__call__
        
        async def patched_write_call(self, params):
            # 获取原始文件内容（如果存在）
            from kaos.path import KaosPath
            p = KaosPath(params.path).expanduser().canonical()
            
            old_text = ""
            if await p.exists():
                old_text = await p.read_text(errors="replace") or ""
            
            # 调用原始方法
            result = await original_write_call(self, params)
            
            # 如果成功，记录修改
            if not result.is_error:
                new_text = params.content
                if params.mode == "append" and old_text:
                    new_text = old_text + params.content
                
                _mod_tracker.record_change(str(p), old_text, new_text)
                KimiSoulPatch.record_tool_call("WriteFile")
            
            return result
        
        WriteFile.__call__ = patched_write_call
        
        # Hook StrReplaceFile
        original_replace_call = StrReplaceFile.__call__
        
        async def patched_replace_call(self, params):
            from kaos.path import KaosPath
            p = KaosPath(params.path).expanduser().canonical()
            
            old_text = ""
            if await p.exists():
                old_text = await p.read_text(errors="replace") or ""
            
            # 调用原始方法
            result = await original_replace_call(self, params)
            
            # 如果成功，记录修改
            if not result.is_error:
                # 读取新内容
                new_text = await p.read_text(errors="replace") or ""
                _mod_tracker.record_change(str(p), old_text, new_text)
                KimiSoulPatch.record_tool_call("StrReplaceFile")
            
            return result
        
        StrReplaceFile.__call__ = patched_replace_call
    
    def _patch_status_snapshot(self) -> None:
        """扩展StatusSnapshot以包含修改信息。"""
        from kimi_cli.soul import StatusSnapshot
        
        # 添加modification_summary属性
        @property
        def modification_summary(self) -> str:
            return _mod_tracker.format_summary()
        
        StatusSnapshot.modification_summary = modification_summary
    
    def _patch_prompt_render(self) -> None:
        """修改底部状态栏渲染。"""
        from kimi_cli.ui.shell.prompt import CustomPromptSession
        
        original_render = CustomPromptSession._render_bottom_toolbar
        
        def patched_render(self):
            """包装后的渲染方法，添加修改统计。"""
            # 获取原始结果
            from prompt_toolkit.formatted_text import FormattedText
            
            original_result = original_render(self)
            
            # 获取修改统计
            mod_summary = _mod_tracker.format_summary()
            
            if not mod_summary:
                return original_result
            
            # 在原始结果中添加修改统计
            # original_result 是 FormattedText，包含 [(style, text), ...]
            fragments = list(original_result)
            
            # 在右侧内容之前插入修改统计
            # 找到context usage的位置，在其后插入
            for i, (style, text) in enumerate(fragments):
                if "context:" in text:
                    # 在context后插入修改统计
                    fragments.insert(i + 1, ("", "  "))
                    fragments.insert(i + 2, ("fg:#00ff00 bold", f"+{_mod_tracker.total_added}"))
                    fragments.insert(i + 3, ("", "/"))
                    fragments.insert(i + 4, ("fg:#ff0000 bold", f"-{_mod_tracker.total_removed}"))
                    break
            
            return FormattedText(fragments)
        
        CustomPromptSession._render_bottom_toolbar = patched_render


def patch() -> bool:
    """应用修改追踪补丁。"""
    patcher = ModTrackerPatch()
    return patcher.apply()
