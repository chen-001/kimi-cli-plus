"""
AskUser工具 - 交互式用户询问工具

当AI需要用户提供选择或输入时使用此工具。
工具提供交互式UI，支持上下键选择和自定义输入。
"""

from pathlib import Path
from typing import override

from kosong.tooling import BriefDisplayBlock, CallableTool2, ToolReturnValue
from pydantic import BaseModel, Field

from kimi_cli.soul.approval import Approval
from kimi_cli.tools.utils import load_desc


def parse_questionnaire(questionnaire: str) -> tuple[str, str | None, list[str]]:
    """
    解析questionnaire格式的字符串。

    格式：
    [question] 问题内容
    [topic] 主题标签（可选）
    [option] 选项1
    [option] 选项2
    ...

    返回: (question, topic, options)
    """
    lines = questionnaire.strip().split("\n")
    question = ""
    topic = None
    options: list[str] = []

    current_section: str | None = None
    current_content: list[str] = []

    def flush_section():
        nonlocal question, topic, options
        if current_section == "question":
            question = "\n".join(current_content).strip()
        elif current_section == "topic":
            topic = "\n".join(current_content).strip()
        elif current_section == "option":
            opt = "\n".join(current_content).strip()
            if opt:
                options.append(opt)

    for line in lines:
        # Check for section markers
        if line.startswith("[question]"):
            flush_section()
            current_section = "question"
            current_content = []
            remaining = line[len("[question]") :].strip()
            if remaining:
                current_content.append(remaining)
        elif line.startswith("[topic]"):
            flush_section()
            current_section = "topic"
            current_content = []
            remaining = line[len("[topic]") :].strip()
            if remaining:
                current_content.append(remaining)
        elif line.startswith("[option]"):
            flush_section()
            current_section = "option"
            current_content = []
            remaining = line[len("[option]") :].strip()
            if remaining:
                current_content.append(remaining)
        elif current_section:
            current_content.append(line)

    flush_section()

    # 如果没有使用格式标记，将整个文本作为问题
    if not question and questionnaire.strip():
        question = questionnaire.strip()

    # 自动添加"自定义输入"选项（如果提供了其他选项且最后一个不是自定义输入）
    if options and not any(
        opt.startswith("✏️") or "自定义" in opt or "own answer" in opt.lower()
        for opt in options
    ):
        options.append("✏️ 自定义输入（选择此项后输入你的答案）")

    return question, topic, options


class AskUserParams(BaseModel):
    """AskUser工具的参数。"""

    questionnaire: str = Field(
        description="""要询问用户的问题，支持格式化输入。

格式示例：
[question] 您想要选择哪种方案？
[topic] 方案选择
[option] 方案A：快速实现
[option] 方案B：稳定优先
[option] 方案C：功能完整

说明：
- [question]: 问题内容（必须）
- [topic]: 简短主题标签，用于UI导航（可选）
- [option]: 选项列表（可选，每行一个）

用户可以：
1. 使用上下键浏览选项
2. 按Enter选择
3. 在"自定义输入"选项输入自己的答案

注意：系统会自动在选项列表最后添加"✏️ 自定义输入"选项，无需手动添加。"""
    )


class AskUserResult(BaseModel):
    """AskUser工具的结果。"""

    response: str = Field(description="用户的回答或选择")
    choice_index: int | None = Field(
        default=None, description="如果从预设选项中选择，这是选项的索引"
    )
    is_custom: bool = Field(default=False, description="是否为用户自定义输入")
    cancelled: bool = Field(default=False, description="用户是否取消了回答")


class AskUser(CallableTool2[AskUserParams]):
    """
    向用户提问或请求选择的交互式工具。

    使用场景：
    1. 用户请求提供选项时 - "给我一些选项"、"有哪些选择"
    2. 有多种可行方案时 - 需要用户决定采用哪种方式
    3. 需要澄清时 - 用户指令不明确
    4. 需要额外信息时 - 用户必须提供特定输入

    重要：
    - 当有多个选项需要用户选择时，必须使用此工具
    - 不要在响应中列出选项，而是通过工具展示
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
            # 解析questionnaire格式（会自动添加"自定义输入"选项）
            question, topic, options = parse_questionnaire(params.questionnaire)

            if not question:
                return ToolReturnValue(
                    is_error=True,
                    output="",
                    message="No question provided in questionnaire",
                    display=[BriefDisplayBlock(text="❌ 未提供问题内容")],
                )

            # 创建显示内容
            display_blocks = []

            # 添加问题标题
            if topic:
                display_blocks.append(BriefDisplayBlock(text=f"[{topic}]"))
            display_blocks.append(BriefDisplayBlock(text=f"❓ {question}"))

            # 添加选项
            if options:
                options_text = "\n".join(f"  {i + 1}. {opt}" for i, opt in enumerate(options))
                display_blocks.append(BriefDisplayBlock(text=f"\n选项:\n{options_text}"))

            # 通过approval系统发起询问
            if self._approval is not None:
                approved = await self._approval.request(
                    sender=self.name,
                    action="ask_user_inquiry",
                    description=question,
                    display=display_blocks,
                    options=options if options else None,
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

                # 获取用户响应
                user_response = self._approval.get_user_response()

                # 判断是否为自定义输入
                is_custom = False
                choice_index = None

                if user_response:
                    # 检查是否匹配预设选项
                    for i, opt in enumerate(options):
                        if opt == user_response:
                            choice_index = i
                            break
                    else:
                        # 不匹配任何预设选项，说明是自定义输入
                        is_custom = bool(options)

                result = AskUserResult(
                    response=user_response or "",
                    choice_index=choice_index,
                    is_custom=is_custom,
                    cancelled=False,
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
