"""
功能3: 统计信息 Patch
=====================

在每次AI回答结束后显示：
- TPS (tokens per second)
- 首个token延迟
- 本次回答用时
- API请求次数
- 工具调用次数
- 修改代码行数
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from kimi_cli.plugins.core import PatchBase


@dataclass
class TurnStats:
    """单次Turn的统计信息。"""

    turn_start_time: float = field(default_factory=time.time)
    first_token_time: float | None = None
    api_calls: int = 0
    tool_calls: int = 0
    lines_added: int = 0
    lines_removed: int = 0
    total_tokens: int = 0
    completion_tokens: int = 0

    @property
    def total_time_ms(self) -> int:
        """总用时（毫秒）。"""
        return int((time.time() - self.turn_start_time) * 1000)

    @property
    def first_token_latency_ms(self) -> int | None:
        """首个token延迟（毫秒）。"""
        if self.first_token_time is None:
            return None
        return int((self.first_token_time - self.turn_start_time) * 1000)

    @property
    def tps(self) -> float | None:
        """TPS (tokens per second)。"""
        if not self.completion_tokens or not self.first_token_time:
            return None
        generation_time = time.time() - self.first_token_time
        if generation_time <= 0:
            return None
        return round(self.completion_tokens / generation_time, 1)

    def format_display(self) -> str:
        """格式化为显示字符串。"""
        parts = []

        # 时间和TPS
        if self.first_token_latency_ms is not None:
            parts.append(f"⏱️ 首token: {self.first_token_latency_ms}ms")

        parts.append(f"⏳ 总用时: {self.total_time_ms // 1000}.{self.total_time_ms % 1000:03d}s")

        if self.tps is not None:
            parts.append(f"⚡ TPS: {self.tps}")

        # API和工具
        parts.append(f"🌐 API: {self.api_calls}")
        parts.append(f"🔧 工具: {self.tool_calls}")

        # 代码修改
        if self.lines_added or self.lines_removed:
            parts.append(f"📝 代码: +{self.lines_added}/-{self.lines_removed}")

        return " | ".join(parts)


class KimiSoulPatch(PatchBase):
    """KimiSoul层的补丁，用于收集和显示统计信息。"""

    # 类级别的当前统计对象
    _current_stats: TurnStats | None = None

    def get_patch_name(self) -> str:
        return "kimisoul_stats"

    def apply(self) -> bool:
        """应用补丁。"""
        try:
            self._patch_turn_method()
            self._patch_step_method()
            self._patch_run_method()
            self._patch_toolset_method()
            print(f"[Plugin] {self.get_patch_name()} applied successfully")
            return True
        except Exception as e:
            print(f"[Plugin] Failed to apply {self.get_patch_name()}: {e}")
            import traceback

            traceback.print_exc()
            return False

    def _patch_turn_method(self) -> None:
        """包装 _turn 方法以追踪整个Turn。"""
        from kimi_cli.soul.kimisoul import KimiSoul

        original_turn = KimiSoul._turn

        async def patched_turn(self, user_message):
            """包装后的_turn方法。"""
            # 调用原始方法
            result = await original_turn(self, user_message)
            return result

        KimiSoul._turn = patched_turn

    def _patch_run_method(self) -> None:
        """重写 run 方法以在 TurnEnd 中附加统计信息。"""
        from collections.abc import Awaitable

        from kosong.message import Message

        from kimi_cli.soul import wire_send
        from kimi_cli.soul.kimisoul import KimiSoul
        from kimi_cli.utils.slashcmd import parse_slash_command_call
        from kimi_cli.wire.types import TextPart, TurnBegin, TurnEnd

        # 保存原始方法引用，以便在需要时调用
        original_turn = KimiSoul._turn

        async def patched_run(self, user_input):
            """重写后的run方法：在 TurnEnd 中附加统计信息。"""
            # 初始化统计
            KimiSoulPatch._current_stats = TurnStats()

            # Refresh OAuth tokens on each turn to avoid idle-time expirations.
            await self._runtime.oauth.ensure_fresh(self._runtime)

            wire_send(TurnBegin(user_input=user_input))
            user_message = Message(role="user", content=user_input)
            text_input = user_message.extract_text(" ").strip()

            if command_call := parse_slash_command_call(text_input):
                command = self._find_slash_command(command_call.name)
                if command is None:
                    wire_send(TextPart(text=f'Unknown slash command "/{command_call.name}".'))
                else:
                    ret = command.func(self, command_call.args)
                    if isinstance(ret, Awaitable):
                        await ret
            elif self._loop_control.max_ralph_iterations != 0:
                # 使用原始 FlowRunner
                from kimi_cli.soul.kimisoul import FlowRunner

                runner = FlowRunner.ralph_loop(
                    user_message,
                    self._loop_control.max_ralph_iterations,
                )
                await runner.run(self, "")
            else:
                await original_turn(self, user_message)

            # 发送带统计信息的 TurnEnd
            stats = KimiSoulPatch._current_stats
            if stats:
                wire_send(TurnEnd(stats_text=stats.format_display()))
                KimiSoulPatch._current_stats = None
            else:
                wire_send(TurnEnd())

        KimiSoul.run = patched_run

    def _patch_step_method(self) -> None:
        """包装 _step 方法以追踪API调用和首个token。"""
        from kosong.message import TextPart, ThinkPart

        import kimi_cli.soul.kimisoul as kimisoul_module
        from kimi_cli.soul.kimisoul import KimiSoul
        from kimi_cli.wire.types import StatusUpdate, ToolCall, ToolCallPart

        # 保存原始方法
        original_step = KimiSoul._step

        async def patched_step(self):
            """包装后的_step方法。"""
            stats = KimiSoulPatch._current_stats

            # 增加API调用计数
            if stats:
                stats.api_calls += 1

            # 拦截 wire_send 来检测首个token和token使用情况
            import kimi_cli.soul

            original_wire_send = kimi_cli.soul.wire_send
            original_wire_send_in_kimisoul = kimisoul_module.wire_send

            def wrapped_wire_send(msg):
                """包装wire_send以检测首个内容部分和token使用情况。"""
                # 检测首个token（任何AI响应：文本、思考、工具调用）
                if (
                    stats
                    and stats.first_token_time is None
                    and isinstance(msg, (TextPart, ThinkPart, ToolCall, ToolCallPart))
                ):
                    stats.first_token_time = time.time()

                return original_wire_send(msg)

            # 临时替换两个地方的 wire_send
            # 1. kimi_cli.soul.wire_send - 供其他代码动态获取
            # 2. kimisoul_module.wire_send - _step方法中on_message_part实际使用的
            kimi_cli.soul.wire_send = wrapped_wire_send
            kimisoul_module.wire_send = wrapped_wire_send

            try:
                # 调用原始 _step 方法
                result = await original_step(self)

                # 在恢复 wire_send 之前，手动记录 token usage
                # 因为 _step 内部会在最后发送 StatusUpdate，但那时 wire_send 已经被恢复了
                if stats and result and hasattr(result, 'usage') and result.usage:
                    KimiSoulPatch.record_token_usage(result.usage)

                # 恢复 wire_send
                kimi_cli.soul.wire_send = original_wire_send
                kimisoul_module.wire_send = original_wire_send_in_kimisoul

                return result
            except Exception:
                # 恢复 wire_send
                kimi_cli.soul.wire_send = original_wire_send
                kimisoul_module.wire_send = original_wire_send_in_kimisoul
                raise

        KimiSoul._step = patched_step

    def _patch_toolset_method(self) -> None:
        """包装 KimiToolset.handle 方法以追踪工具调用。"""
        from kimi_cli.soul.toolset import KimiToolset

        original_handle = KimiToolset.handle

        def patched_handle(self, tool_call):
            """包装后的handle方法。"""
            # 记录工具调用
            stats = KimiSoulPatch._current_stats
            if stats:
                stats.tool_calls += 1

            # 调用原始方法
            return original_handle(self, tool_call)

        KimiToolset.handle = patched_handle

    @classmethod
    def record_tool_call(cls, tool_name: str) -> None:
        """记录工具调用。供其他补丁调用。"""
        stats = cls._current_stats
        if stats:
            stats.tool_calls += 1

    @classmethod
    def record_code_change(cls, lines_added: int = 0, lines_removed: int = 0) -> None:
        """记录代码修改。供其他补丁调用。"""
        stats = cls._current_stats
        if stats:
            stats.lines_added += lines_added
            stats.lines_removed += lines_removed

    @classmethod
    def record_token_usage(cls, usage: Any) -> None:
        """记录token使用情况。"""
        stats = cls._current_stats
        if stats and usage:
            from kosong.chat_provider import TokenUsage

            if isinstance(usage, TokenUsage):
                stats.total_tokens = usage.total or 0
                stats.completion_tokens = usage.output or 0


def patch() -> bool:
    """应用KimiSoul补丁。"""
    patcher = KimiSoulPatch()
    return patcher.apply()
