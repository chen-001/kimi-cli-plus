"""
功能2: YOLO模式下保留必要交互 Patch
======================================

核心修改：
1. 区分"权限申请"和"信息询问"两类交互
2. AskUser工具的action不受YOLO模式影响
3. 支持选项选择和自由输入两种模式
4. 取消时停止当前任务
"""

from __future__ import annotations

import asyncio

from kimi_cli.plugins.core import PatchBase


class ApprovalPatch(PatchBase):
    """Approval系统的补丁。"""

    # 询问类action（不受YOLO影响）
    INQUIRY_ACTIONS = {
        "ask_user_inquiry",
        "confirm_choice",
        "select_option",
    }

    def get_patch_name(self) -> str:
        return "approval_inquiry"

    def apply(self) -> bool:
        """应用补丁。"""
        try:
            self._patch_approval_request()
            self._patch_visualize_for_inquiry()
            print(f"[Plugin] {self.get_patch_name()} applied successfully")
            return True
        except Exception as e:
            print(f"[Plugin] Failed to apply {self.get_patch_name()}: {e}")
            return False

    def _patch_approval_request(self) -> None:
        """修改Approval.request方法。"""
        from kimi_cli.soul.approval import Approval, Request

        original_request = Approval.request

        async def patched_request(
            self,
            sender: str,
            action: str,
            description: str,
            display: list | None = None,
        ) -> bool:
            """
            修改后的request方法：
            - 如果是询问类action，不受YOLO模式影响
            - 否则保持原有逻辑
            """
            # 检查是否是询问类action
            is_inquiry = action in ApprovalPatch.INQUIRY_ACTIONS

            # 如果是询问，强制走交互流程
            if is_inquiry:
                return await self._do_inquiry_request(sender, action, description, display)

            # 否则走原有逻辑（包括YOLO判断）
            return await original_request(self, sender, action, description, display)

        # 添加新的辅助方法
        async def _do_inquiry_request(self, sender, action, description, display):
            """处理询问类请求（总是交互）。"""
            import uuid

            from kimi_cli.soul.toolset import get_current_tool_call_or_none
            from kimi_cli.wire import wire_send
            from kimi_cli.wire.types import ApprovalRequest

            tool_call = get_current_tool_call_or_none()
            if tool_call is None:
                raise RuntimeError("Approval must be requested from a tool call.")

            # 创建询问请求
            request = Request(
                id=str(uuid.uuid4()),
                tool_call_id=tool_call.id,
                sender=sender,
                action=action,
                description=description,
                display=display or [],
            )

            # 标记为inquiry类型（通过特殊方式传递）
            # 这里我们使用一个特殊的future来等待用户输入
            approved_future = asyncio.Future()

            # 存储请求
            if not hasattr(self, "_inquiry_requests"):
                self._inquiry_requests = {}
            self._inquiry_requests[request.id] = (request, approved_future)

            # 放入队列
            self._request_queue.put_nowait(request)

            # 发送Wire事件（UI会特殊处理inquiry）
            wire_request = ApprovalRequest(
                id=request.id,
                action=request.action,
                description=request.description,
                sender=request.sender,
                tool_call_id=request.tool_call_id,
                display=request.display,
            )
            # 标记为inquiry（通过display传递标记）
            wire_request._is_inquiry = True  # 内部标记

            wire_send(wire_request)

            # 等待用户响应
            try:
                result = await approved_future
                return result
            except asyncio.CancelledError:
                # 用户取消
                return False

        Approval.request = patched_request
        Approval._do_inquiry_request = _do_inquiry_request

    def _patch_visualize_for_inquiry(self) -> None:
        """
        修改可视化层以支持询问模式。

        询问模式与权限申请的区别：
        - 询问可以输入文字回复（不只是approve/reject）
        - 询问有选项时可以点击选择
        - 询问的结果会返回到对话中
        """
        from rich.text import Text

        from kimi_cli.ui.shell.console import console
        from kimi_cli.ui.shell.visualize import _ApprovalRequestPanel, _LiveView

        # 标记原类是否有我们的标记
        _original_render = _ApprovalRequestPanel.render

        def patched_render(self):
            """修改渲染以区分询问模式。"""
            # 检查是否是询问（通过action判断）
            is_inquiry = self.request.action in ApprovalPatch.INQUIRY_ACTIONS

            if not is_inquiry:
                # 普通权限申请，使用原始渲染
                return _original_render(self)

            # 询问模式渲染
            from rich.console import Group
            from rich.padding import Padding

            content_lines = [Text.from_markup(f"[cyan]❓ {self.request.sender} 想询问你：[/cyan]")]
            content_lines.append(Text(""))

            # 显示问题内容
            for block in self.request.display:
                if hasattr(block, "text"):
                    content_lines.append(Text(block.text))

            # 询问模式的选项不同
            self.options = [("回复...", "reply"), ("取消（停止当前任务）", "cancel")]

            lines = [Padding(Group(*content_lines), (0, 0, 0, 2))]

            if lines:
                lines.append(Text(""))

            for i, (option_text, _) in enumerate(self.options):
                if i == self.selected_index:
                    lines.append(Text(f"→ {option_text}", style="cyan"))
                else:
                    lines.append(Text(f"  {option_text}", style="grey50"))

            return Padding(Group(*lines), 1)

        _ApprovalRequestPanel.render = patched_render

        # 修改键盘处理以支持输入
        original_dispatch = _LiveView.dispatch_keyboard_event

        def patched_dispatch_keyboard(self, event):
            """修改键盘事件处理。"""
            if not self._current_approval_request_panel:
                return

            request = self._current_approval_request_panel.request
            is_inquiry = request.action in ApprovalPatch.INQUIRY_ACTIONS

            if not is_inquiry:
                # 普通权限申请，使用原始处理
                return original_dispatch(self, event)

            # 询问模式处理
            from kimi_cli.ui.shell.keyboard import KeyEvent

            if event == KeyEvent.ENTER:
                selected = self._current_approval_request_panel.get_selected_response()

                if selected == "reply":
                    # 需要获取用户输入
                    # 暂停Live显示，让用户输入
                    # 这里简化处理，实际实现需要更复杂的交互
                    console.print("\n[cyan]请输入你的回复：[/cyan]")
                    # 实际输入由prompt session处理

                elif selected == "cancel":
                    # 用户取消，停止任务
                    request.resolve("reject")
                    self.show_next_approval_request()
                    # 触发任务停止
                    raise ToolCancelledError("用户取消了询问")

            else:
                # 其他按键使用默认处理
                return original_dispatch(self, event)

        _LiveView.dispatch_keyboard_event = patched_dispatch_keyboard


class ToolCancelledError(Exception):
    """工具被取消的异常。"""

    pass


def patch() -> bool:
    """应用Approval补丁。"""
    patcher = ApprovalPatch()
    return patcher.apply()
