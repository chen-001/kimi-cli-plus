"""
AskUser工具 - 让AI在YOLO模式下也能与用户交互

这个工具允许AI向用户提问或请求选择，即使在YOLO模式下也会暂停等待用户回复。
"""

from __future__ import annotations

from typing import Literal
try:
    from typing import override
except ImportError:
    from typing_extensions import override

from kosong.tooling import CallableTool2, ToolReturnValue
from pydantic import BaseModel, Field


class AskUserParams(BaseModel):
    """AskUser工具的参数。"""
    
    question: str = Field(
        description="要问用户的问题"
    )
    options: list[str] | None = Field(
        default=None,
        description="选项列表。如果提供，用户必须从选项中选择；如果不提供，用户可以自由输入"
    )
    require_input: bool = Field(
        default=True,
        description="是否需要用户输入。如果为false且提供了options，则只需用户确认即可"
    )


class AskUserResult(BaseModel):
    """AskUser工具的结果。"""
    
    response: str = Field(description="用户的回答或选择")
    choice_index: int | None = Field(
        default=None,
        description="如果提供了选项，这是用户选择的索引"
    )
    cancelled: bool = Field(
        default=False,
        description="用户是否取消了回答"
    )


class AskUser(CallableTool2[AskUserParams]):
    """
    向用户提问或请求选择的工具。
    
    这是专门为YOLO模式设计的工具。在YOLO模式下，危险操作（如文件修改）会自动批准，
    但信息确认（如询问细节、请求选择）仍需要用户交互。使用此工具可以确保即使在
    YOLO模式下，AI也能与用户进行必要的沟通。
    
    使用场景：
    1. 用户指令不明确，需要澄清时
    2. 有多个可行方案，需要用户选择时
    3. 执行关键操作前需要最终确认时
    4. 需要用户补充信息时
    
    示例：
    - 用户说"优化代码"但没指定文件 → AskUser("请指定要优化的文件路径")
    - 多个优化方案 → AskUser("请选择优化方向", options=["提速", "省内存", "增强可读性"])
    """
    
    name: str = "AskUser"
    params: type[AskUserParams] = AskUserParams
    
    # 工具描述会在注册时动态加载
    description: str = """
    向用户提问或请求选择。即使在YOLO模式下也会暂停等待用户回复。
    
    当用户指令不够明确、需要补充信息、或需要用户做选择时使用此工具。
    
    参数说明：
    - question: 要问的问题
    - options: 可选的选项列表。提供后用户必须从选项中选择
    - require_input: 是否需要用户输入文字
    
    如果用户取消回答，会返回cancelled=true，当前任务应该停止。
    """.strip()
    
    def __init__(self, approval: Any = None):
        super().__init__()
        self._approval = approval
    
    @override
    async def __call__(self, params: AskUserParams) -> ToolReturnValue:
        """
        执行AskUser工具调用。
        
        实际的处理逻辑在approval_patch中，通过自定义的InquiryRequest实现。
        这里只是返回一个标记，让系统知道需要处理询问。
        """
        # 创建显示内容
        from kimi_cli.tools.display import BriefDisplayBlock
        
        display_blocks = []
        
        # 添加问题
        display_blocks.append(BriefDisplayBlock(text=f"🤔 {params.question}"))
        
        # 添加选项（如果有）
        if params.options:
            options_text = "\n".join(
                f"  {i+1}. {opt}" for i, opt in enumerate(params.options)
            )
            display_blocks.append(BriefDisplayBlock(text=f"\n选项:\n{options_text}"))
        
        # 通过approval系统发起询问
        # 注意：这里依赖approval_patch中修改后的逻辑
        if self._approval is not None:
            # 使用特殊的action来标识这是询问而非权限申请
            approved = await self._approval.request(
                sender=self.name,
                action="ask_user_inquiry",
                description=params.question,
                display=display_blocks,
            )
            
            if not approved:
                # 用户取消
                result = AskUserResult(response="", cancelled=True)
                return ToolReturnValue(
                    is_error=False,
                    output=result.model_dump_json(),
                    message="用户取消了回答",
                )
        
        # 正常情况下，approval系统会处理用户输入
        # 这里返回一个占位结果，实际结果由UI层注入
        result = AskUserResult(
            response="[等待用户输入...]",
            cancelled=False
        )
        
        return ToolReturnValue(
            is_error=False,
            output=result.model_dump_json(),
            message="已向用户发起询问",
        )


# 工具注册函数
def register_ask_user_tool(toolset: Any, runtime: Any) -> None:
    """将AskUser工具注册到toolset中。"""
    from kimi_cli.soul.approval import Approval
    
    approval = runtime.approval if hasattr(runtime, 'approval') else None
    tool = AskUser(approval=approval)
    toolset.register_tool(tool)
