import sys
from pathlib import Path
from typing import override

if sys.version_info < (3, 12):
    raise RuntimeError("AskUser tool requires Python 3.12 or later")

from kosong.tooling import BriefDisplayBlock, CallableTool2, ToolReturnValue
from pydantic import BaseModel, Field

from kimi_cli.soul.approval import Approval
from kimi_cli.tools.utils import load_desc


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
    description: str = load_desc(Path(__file__).parent / "ask_user.md")

    def __init__(self, approval: Approval):
        super().__init__()
        self._approval = approval

    @override
    async def __call__(self, params: AskUserParams) -> ToolReturnValue:
        """
        执行AskUser工具调用。
        
        使用approval系统发起询问，并获取用户选择。
        """
        try:
            # 创建显示内容
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
            if self._approval is not None:
                # 使用特殊的action来标识这是询问而非权限申请
                approved = await self._approval.request(
                    sender=self.name,
                    action="ask_user_inquiry",
                    description=params.question,
                    display=display_blocks,
                    options=params.options,
                )
                
                if not approved:
                    # 用户取消
                    result = AskUserResult(response="", cancelled=True)
                    return ToolReturnValue(
                        is_error=False,
                        output=result.model_dump_json(),
                        message="用户取消了回答",
                        display=display_blocks,
                    )
                
                # 获取用户选择
                user_response = self._approval.get_user_response()
                
                # 解析响应
                choice_index = None
                if params.options and user_response:
                    for i, opt in enumerate(params.options):
                        if opt == user_response:
                            choice_index = i
                            break

                result = AskUserResult(
                    response=user_response or "",
                    choice_index=choice_index,
                    cancelled=False
                )

                return ToolReturnValue(
                    is_error=False,
                    output=result.model_dump_json(),
                    message=f"用户选择: {user_response}",
                    display=display_blocks,
                )
            else:
                # approval 不可用
                return ToolReturnValue(
                    is_error=True,
                    output="",
                    message="Approval system is not available",
                    display=[BriefDisplayBlock(text="❌ Approval system is not available")],
                )
            
        except Exception as e:
            import traceback
            error_msg = f"AskUser error: {type(e).__name__}: {e}\n{traceback.format_exc()}"
            return ToolReturnValue(
                is_error=True,
                output="",
                message=error_msg,
                display=[BriefDisplayBlock(text=f"❌ AskUser error: {e}")],
            )
