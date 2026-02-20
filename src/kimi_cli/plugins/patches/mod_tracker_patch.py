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

    def _count_line_changes(self, old_text: str, new_text: str) -> tuple[int, int]:
        """
        使用 difflib 准确计算增删行数。

        Returns:
            (added_lines, removed_lines)
        """
        from difflib import SequenceMatcher

        old_lines = old_text.splitlines() if old_text else []
        new_lines = new_text.splitlines() if new_text else []

        added = 0
        removed = 0

        sm = SequenceMatcher(None, old_lines, new_lines)
        for tag, i1, i2, j1, j2 in sm.get_opcodes():
            if tag == "delete":
                removed += i2 - i1
            elif tag == "insert":
                added += j2 - j1
            elif tag == "replace":
                removed += i2 - i1
                added += j2 - j1

        return added, removed

    def record_change(self, path: str, old_text: str, new_text: str) -> None:
        """记录一次文件修改。"""
        added, removed = self._count_line_changes(old_text, new_text)

        if path not in self.file_changes:
            self.file_changes[path] = FileChange(path=path)

        change = self.file_changes[path]
        change.lines_added += added
        change.lines_removed += removed
        change.edit_count += 1

        KimiSoulPatch.record_code_change(lines_added=added, lines_removed=removed)

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
        """格式化为简短摘要（用于显示在底部状态栏）。"""
        if not self.file_changes:
            return ""

        parts = []
        sorted_changes = sorted(
            self.file_changes.values(), key=lambda x: x.lines_added + x.lines_removed, reverse=True
        )

        for change in sorted_changes[:3]:
            short_name = change.path.split("/")[-1].split("\\")[-1]
            parts.append(f"{short_name}: +{change.lines_added}/-{change.lines_removed}")

        result = " | ".join(parts)
        if len(sorted_changes) > 3:
            result += f" (+{len(sorted_changes) - 3} more)"

        return result

    def format_detailed_summary(self) -> str:
        """格式化为详细摘要（包含所有文件）。"""
        if not self.file_changes:
            return "无文件修改"

        lines = []
        lines.append(f"总计: +{self.total_added}/-{self.total_removed} ({self.total_files} files)")

        sorted_changes = sorted(
            self.file_changes.values(), key=lambda x: x.lines_added + x.lines_removed, reverse=True
        )

        for change in sorted_changes:
            lines.append(f"  {change.path}: +{change.lines_added}/-{change.lines_removed}")

        return "\n".join(lines)


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
            self._patch_stats_display()
            print(f"[Plugin] {self.get_patch_name()} applied successfully")
            return True
        except Exception as e:
            print(f"[Plugin] Failed to apply {self.get_patch_name()}: {e}")
            return False

    def _patch_file_tools(self) -> None:
        """Hook文件修改工具。"""
        from kimi_cli.tools.file.replace import StrReplaceFile
        from kimi_cli.tools.file.write import WriteFile

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

                tracker = get_mod_tracker()
                tracker.record_change(str(p), old_text, new_text)
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
                new_text = await p.read_text(errors="replace") or ""
                tracker = get_mod_tracker()
                tracker.record_change(str(p), old_text, new_text)
                KimiSoulPatch.record_tool_call("StrReplaceFile")

            return result

        StrReplaceFile.__call__ = patched_replace_call

    def _patch_status_snapshot(self) -> None:
        """扩展StatusSnapshot以包含修改信息。"""
        from kimi_cli.soul import StatusSnapshot

        @property
        def modification_summary(self) -> str:
            return get_mod_tracker().format_summary()

        StatusSnapshot.modification_summary = modification_summary

    def _patch_prompt_render(self) -> None:
        """修改底部状态栏渲染，支持多行显示文件修改统计，自动换行。"""
        from kimi_cli.ui.shell.prompt import CustomPromptSession

        original_render = CustomPromptSession._render_bottom_toolbar

        def patched_render(self):
            """包装后的渲染方法，添加修改统计。"""
            try:
                from prompt_toolkit.formatted_text import FormattedText

                # 获取原始结果
                original_result = original_render(self)

                # 获取修改统计
                tracker = get_mod_tracker()
                total_added = tracker.total_added
                total_removed = tracker.total_removed

                # 如果没有修改，直接返回原始结果
                if not tracker.file_changes:
                    return original_result

                # 获取终端宽度
                from prompt_toolkit.application import get_app_or_none

                app = get_app_or_none()
                columns = 80
                if app is not None:
                    columns = app.output.get_size().columns

                # 准备文件统计数据
                file_stats = []
                for change in tracker.file_changes.values():
                    short_name = change.path.split("/")[-1].split("\\")[-1]
                    file_stats.append(
                        {
                            "name": short_name,
                            "added": change.lines_added,
                            "removed": change.lines_removed,
                            "text": f"{short_name}: +{change.lines_added}/-{change.lines_removed}",
                        }
                    )

                # 构建文件统计行，自动换行
                prefix = f"📁 +{total_added}/-{total_removed}"
                separator = " | "
                indent = "  "

                lines = []
                current_line_fragments = []
                current_line_width = 0

                # 添加前缀
                prefix_full = prefix + " | "
                current_line_fragments.append(("fg:#00aa00", prefix))
                current_line_fragments.append(("", " | "))
                current_line_width = len(prefix_full)

                # 逐个添加文件统计
                for i, stat in enumerate(file_stats):
                    stat_text = stat["text"]
                    stat_width = len(stat_text)
                    sep_width = len(separator) if i > 0 else 0

                    # 检查是否需要换行
                    line_would_overflow = current_line_width + sep_width + stat_width > columns
                    if line_would_overflow and current_line_fragments:
                        lines.append(current_line_fragments)
                        current_line_fragments = []
                        current_line_width = 0
                        current_line_fragments.append(("", indent))
                        current_line_width = len(indent)

                    # 添加分隔符
                    if i > 0 and current_line_width > len(indent):
                        current_line_fragments.append(("", separator))
                        current_line_width += len(separator)

                    # 添加文件统计
                    current_line_fragments.append(("", f"{stat['name']}: "))
                    current_line_fragments.append(("fg:#00ff00 bold", f"+{stat['added']}"))
                    current_line_fragments.append(("", "/"))
                    current_line_fragments.append(("fg:#ff0000 bold", f"-{stat['removed']}"))
                    current_line_width += len(stat_text)

                # 保存最后一行
                if current_line_fragments:
                    lines.append(current_line_fragments)

                # 合并所有 fragment
                fragments = list(original_result)

                # 添加文件统计行
                for line_fragments in lines:
                    fragments.append(("", "\n"))
                    fragments.extend(line_fragments)

                return FormattedText(fragments)
            except Exception:
                return original_render(self)

        CustomPromptSession._render_bottom_toolbar = patched_render

    def _patch_stats_display(self) -> None:
        """
        修改 TurnEnd 的统计信息显示。
        移除代码统计从 TurnEnd 面板，因为现在显示在底部状态栏。
        """
        from kimi_cli.ui.shell.visualize import _LiveView
        from kimi_cli.wire.types import TurnEnd

        original_dispatch = _LiveView.dispatch_wire_message

        def patched_dispatch(self, msg):
            """包装后的 dispatch，修改 TurnEnd 的显示。"""
            if isinstance(msg, TurnEnd) and msg.stats_text:
                import re

                stats_text = msg.stats_text
                stats_text = re.sub(r"\|?\s*📝 代码: \+\d+/-\d+", "", stats_text)
                stats_text = stats_text.strip()
                stats_text = re.sub(r"^\s*\|\s*\|\s*$", "", stats_text)

                msg = msg.model_copy(update={"stats_text": stats_text if stats_text else None})

            return original_dispatch(self, msg)

        _LiveView.dispatch_wire_message = patched_dispatch


def patch() -> bool:
    """应用修改追踪补丁。"""
    patcher = ModTrackerPatch()
    return patcher.apply()
