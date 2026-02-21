"""
AskUser工具 - 交互式用户询问工具（plugins版本）

这是tools/ask_user的别名，保持向后兼容。
"""

# 从主工具导入，保持一致性
from kimi_cli.tools.ask_user import (
    AskUser,
    AskUserParams,
    AskUserResult,
    parse_questionnaire,
)

__all__ = ["AskUser", "AskUserParams", "AskUserResult", "parse_questionnaire"]
