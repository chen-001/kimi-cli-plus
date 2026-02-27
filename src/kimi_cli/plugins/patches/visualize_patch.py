"""
功能5: Diff持久展示 Patch
==========================

修改 visualize.py，在文件修改工具执行完成后，
即使不在approval模式下，也显示带颜色的diff。

这样用户可以在YOLO模式下或approval通过后，仍然看到修改的具体内容。
"""

from __future__ import annotations

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
        from rich.panel import Panel
        from rich.text import Text

        from kimi_cli.tools.display import DiffDisplayBlock
        from kimi_cli.ui.shell.console import console
        from kimi_cli.ui.shell.visualize import _ToolCallBlock

        def _is_diff_view_enabled() -> bool:
            """检查 diff view 是否启用。"""
            try:
                from kimi_cli.ui.shell.diff_view_state import is_diff_view_enabled as get_state

                return get_state()
            except Exception:
                return True

        # 备份原始方法
        original_finish = _ToolCallBlock.finish

        def format_diff_with_highlight(
            old_text: str,
            new_text: str,
            path: str,
            old_start_line: int = 1,
            new_start_line: int = 1,
        ) -> list:
            """
            格式化 diff 并添加颜色高亮和行号。

            Args:
                old_text: 旧文本内容
                new_text: 新文本内容
                path: 文件路径
                old_start_line: 旧文件起始行号（1-based）
                new_start_line: 新文件起始行号（1-based）

            返回 Rich renderable 对象列表。
            """
            from difflib import SequenceMatcher

            from rich.text import Text

            old_lines = old_text.splitlines()
            new_lines = new_text.splitlines()

            result = []

            # 使用 SequenceMatcher 获取差异
            sm = SequenceMatcher(None, old_lines, new_lines)

            for tag, i1, i2, j1, j2 in sm.get_opcodes():
                if tag == "equal":
                    # 未改动的行 - 显示上下文
                    for idx, line in enumerate(old_lines[i1:i2]):
                        old_line_num = old_start_line + i1 + idx
                        new_line_num = new_start_line + j1 + idx
                        # 创建行号列和内容列
                        line_text = Text()
                        # 旧行号
                        line_text.append(f"{old_line_num:4d}", style="dim")
                        line_text.append(" ")
                        # 新行号
                        line_text.append(f"{new_line_num:4d}", style="dim")
                        line_text.append("  ")
                        # 内容 - 无底色
                        line_text.append(f" {line}")
                        result.append(line_text)
                elif tag == "delete":
                    # 删除的行 - 红色
                    for idx, line in enumerate(old_lines[i1:i2]):
                        old_line_num = old_start_line + i1 + idx
                        line_text = Text()
                        # 旧行号
                        line_text.append(f"{old_line_num:4d}", style="red dim")
                        line_text.append(" ")
                        # 新行号（空）
                        line_text.append("    ", style="dim")
                        line_text.append("  ")
                        # 内容 - 红色底色
                        line_text.append(f"-{line}", style="on red")
                        result.append(line_text)
                elif tag == "insert":
                    # 增加的行 - 绿色
                    for idx, line in enumerate(new_lines[j1:j2]):
                        new_line_num = new_start_line + j1 + idx
                        line_text = Text()
                        # 旧行号（空）
                        line_text.append("    ", style="dim")
                        line_text.append(" ")
                        # 新行号
                        line_text.append(f"{new_line_num:4d}", style="green dim")
                        line_text.append("  ")
                        # 内容 - 绿色底色
                        line_text.append(f"+{line}", style="on green")
                        result.append(line_text)
                elif tag == "replace":
                    # 替换的行 - 先显示删除，再显示增加
                    # 删除的部分
                    for idx, line in enumerate(old_lines[i1:i2]):
                        old_line_num = old_start_line + i1 + idx
                        line_text = Text()
                        line_text.append(f"{old_line_num:4d}", style="red dim")
                        line_text.append(" ")
                        line_text.append("    ", style="dim")
                        line_text.append("  ")
                        line_text.append(f"-{line}", style="on red")
                        result.append(line_text)
                    # 增加的部分
                    for idx, line in enumerate(new_lines[j1:j2]):
                        new_line_num = new_start_line + j1 + idx
                        line_text = Text()
                        line_text.append("    ", style="dim")
                        line_text.append(" ")
                        line_text.append(f"{new_line_num:4d}", style="green dim")
                        line_text.append("  ")
                        line_text.append(f"+{line}", style="on green")
                        result.append(line_text)

            return result

        def patched_finish(self, result):
            """包装后的finish方法，添加diff显示。"""
            # 调用原始方法
            original_finish(self, result)

            # 检查是否启用了 diff view
            if not _is_diff_view_enabled():
                return

            # 检查是否是文件修改工具且有diff信息
            if not hasattr(result, "display") or not result.display:
                return

            # 查找diff blocks
            diff_blocks = [block for block in result.display if isinstance(block, DiffDisplayBlock)]

            if not diff_blocks:
                return

            # 获取工具名用于显示
            tool_name = getattr(self, "_tool_name", "Unknown")

            # 渲染diff（带颜色）
            console.print()  # 空行
            console.print(
                Panel(
                    Text(f"📄 {tool_name} - 文件修改详情", style="bold cyan"),
                    border_style="cyan",
                    padding=(0, 1),
                )
            )

            last_path = None
            for block in diff_blocks:
                # 只在路径变化时显示文件路径
                if block.path != last_path:
                    console.print(f"\n[bold]{block.path}[/bold]")
                    last_path = block.path

                # 格式化并显示diff（带语法高亮和行号）
                diff_lines = format_diff_with_highlight(
                    block.old_text,
                    block.new_text,
                    block.path,
                    block.old_start_line,
                    block.new_start_line,
                )

                # 打印表头
                header = Text()
                header.append(" OLD", style="dim")
                header.append(" ")
                header.append(" NEW", style="dim")
                header.append("  ")
                header.append(" 修改内容")
                console.print(header, style="dim")
                console.print(Text("─" * 80, style="dim"))

                # 打印每一行
                for line in diff_lines:
                    console.print(line)

            console.print()  # 空行

        # 应用补丁
        _ToolCallBlock.finish = patched_finish


def patch() -> bool:
    """应用可视化补丁。"""
    patcher = VisualizePatch()
    return patcher.apply()
