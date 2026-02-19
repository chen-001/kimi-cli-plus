"""
功能5: Diff持久展示 Patch
==========================

修改 visualize.py，在文件修改工具执行完成后，
即使不在approval模式下，也显示带颜色的diff。

这样用户可以在YOLO模式下或approval通过后，仍然看到修改的具体内容。
"""

from __future__ import annotations

from typing import Any

from kimi_cli.plugins.core import PatchBase


class VisualizePatch(PatchBase):
    """可视化层的补丁。"""
    
    def get_patch_name(self) -> str:
        return "visualize_diff_display"
    
    def apply(self) -> bool:
        """应用补丁。"""
        try:
            self._patch_tool_call_block()
            print(f"[Plugin] {self.get_patch_name()} applied successfully")
            return True
        except Exception as e:
            print(f"[Plugin] Failed to apply {self.get_patch_name()}: {e}")
            return False
    
    def _patch_tool_call_block(self) -> None:
        """
        修补 _ToolCallBlock.finish 方法，在文件修改完成后显示diff。
        """
        from kimi_cli.ui.shell.visualize import _ToolCallBlock
        from kimi_cli.tools.display import DiffDisplayBlock
        from kosong.tooling import BriefDisplayBlock
        from kimi_cli.ui.shell.console import console
        from kimi_cli.utils.diff import format_unified_diff
        from rich.syntax import Syntax
        from rich.panel import Panel
        from rich.text import Text
        
        # 备份原始方法
        original_finish = _ToolCallBlock.finish
        
        def patched_finish(self, result):
            """包装后的finish方法，添加diff显示。"""
            # 调用原始方法
            original_finish(self, result)
            
            # 检查是否是文件修改工具且有diff信息
            if not hasattr(result, 'display') or not result.display:
                return
            
            # 查找diff blocks
            diff_blocks = [
                block for block in result.display 
                if isinstance(block, DiffDisplayBlock)
            ]
            
            if not diff_blocks:
                return
            
            # 获取工具名用于显示
            tool_name = getattr(self, '_tool_name', 'Unknown')
            
            # 渲染diff（带颜色）
            console.print()  # 空行
            console.print(
                Panel(
                    Text(f"📄 {tool_name} - 文件修改详情", style="bold cyan"),
                    border_style="cyan",
                    padding=(0, 1)
                )
            )
            
            last_path = None
            for block in diff_blocks:
                # 只在路径变化时显示文件路径
                if block.path != last_path:
                    console.print(f"\n[bold]{block.path}[/bold]")
                    last_path = block.path
                
                # 格式化并显示diff（带语法高亮）
                diff_text = format_unified_diff(
                    block.old_text,
                    block.new_text,
                    block.path,
                    include_file_header=False
                )
                
                # 使用Syntax高亮显示diff
                if diff_text.strip():
                    syntax = Syntax(
                        diff_text,
                        lexer="diff",
                        theme="monokai",
                        line_numbers=False,
                        word_wrap=True
                    )
                    console.print(syntax)
            
            console.print()  # 空行
        
        # 应用补丁
        _ToolCallBlock.finish = patched_finish


def patch() -> bool:
    """应用可视化补丁。"""
    patcher = VisualizePatch()
    return patcher.apply()
