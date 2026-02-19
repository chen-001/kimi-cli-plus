"""
功能2补充: 自动注册 AskUser 工具 + System Prompt 修改
======================================================

在 agent 加载完成后：
1. 自动将 AskUser 工具添加到 toolset 中
2. 在 system prompt 中添加 AskUser 工具使用说明

这样 AI 就可以在需要时使用 AskUser 工具与用户交互。
"""

from __future__ import annotations

from kimi_cli.plugins.core import PatchBase


ASKUSER_TOOL_GUIDANCE = """

## 与用户交互的工具

当你需要向用户提问、请求选择或确认细节时，使用 `AskUser` 工具。

**使用场景：**
1. 用户指令不够明确，需要澄清时
2. 有多个可行方案，需要用户选择时
3. 执行关键操作前需要最终确认时
4. 需要用户补充信息时

**使用方式：**
- 调用 `AskUser` 工具，传入 `question` 参数
- 如果需要用户从选项中选择，提供 `options` 列表
- 如果需要自由输入，不提供 `options`

**示例：**
- 用户说"优化代码"但没指定文件 → AskUser("请指定要优化的文件路径")
- 多个优化方案 → AskUser("请选择优化方向", options=["提速", "省内存", "增强可读性"])

注意：即使在YOLO模式下，AskUser工具也会暂停等待用户回复。

"""


class AskUserToolPatch(PatchBase):
    """AskUser 工具自动注册补丁。"""
    
    def get_patch_name(self) -> str:
        return "askuser_tool_registration"
    
    def apply(self) -> bool:
        """应用补丁。"""
        try:
            self._patch_load_agent()
            print(f"[Plugin] {self.get_patch_name()} applied successfully")
            return True
        except Exception as e:
            print(f"[Plugin] Failed to apply {self.get_patch_name()}: {e}")
            return False
    
    def _patch_load_agent(self) -> None:
        """
        包装 load_agent 函数，在创建 Agent 之前修改 system_prompt。
        """
        from kimi_cli.soul.agent import load_agent, Agent
        
        # 保存原始函数
        original_load_agent = load_agent
        
        async def patched_load_agent(agent_file, runtime, *, mcp_configs):
            """包装后的 load_agent，修改 system_prompt 并添加工具。"""
            # 获取原始代码中的各个步骤，但修改最后创建 Agent 的部分
            from pathlib import Path
            from kimi_cli.agentspec import load_agent_spec
            from kimi_cli.soul.agent import _load_system_prompt
            from kimi_cli.config import Config
            from kimi_cli.soul.agent import BuiltinSystemPromptArgs, DenwaRenji, LaborMarket
            from kimi_cli.utils.environment import Environment
            from kimi_cli.session import Session
            from kimi_cli.llm import LLM
            from kimi_cli.soul.toolset import KimiToolset
            from kimi_cli.utils.logging import logger
            
            logger.info("Loading agent: {agent_file}", agent_file=agent_file)
            agent_spec = load_agent_spec(agent_file)

            # 1. 加载 system prompt 并添加 AskUser 说明
            system_prompt = _load_system_prompt(
                agent_spec.system_prompt_path,
                agent_spec.system_prompt_args,
                runtime.builtin_args,
            )
            # 添加 AskUser 工具使用说明
            if "AskUser" not in system_prompt:
                system_prompt = system_prompt + ASKUSER_TOOL_GUIDANCE
                print(f"[Plugin] AskUser guidance added to system prompt")

            # 2. 加载 subagents（复制原始逻辑）
            for subagent_name, subagent_spec in agent_spec.subagents.items():
                logger.debug("Loading subagent: {subagent_name}", subagent_name=subagent_name)
                subagent = await original_load_agent(
                    subagent_spec.path,
                    runtime.copy_for_fixed_subagent(),
                    mcp_configs=mcp_configs,
                )
                runtime.labor_market.add_fixed_subagent(subagent_name, subagent, subagent_spec.description)

            # 3. 加载 tools
            toolset = KimiToolset()
            tool_deps = {
                KimiToolset: toolset,
                type(runtime): runtime,
                Config: runtime.config,
                BuiltinSystemPromptArgs: runtime.builtin_args,
                Session: runtime.session,
                DenwaRenji: runtime.denwa_renji,
                type(runtime.approval): runtime.approval,
                LaborMarket: runtime.labor_market,
                Environment: runtime.environment,
            }
            
            tools = agent_spec.tools
            if agent_spec.exclude_tools:
                logger.debug("Excluding tools: {tools}", tools=agent_spec.exclude_tools)
                tools = [tool for tool in tools if tool not in agent_spec.exclude_tools]
            
            toolset.load_tools(tools, tool_deps)

            # 4. 添加 AskUser 工具
            from kimi_cli.plugins.tools.ask_user import AskUser
            approval = runtime.approval if hasattr(runtime, 'approval') else None
            ask_user_tool = AskUser(approval=approval)
            toolset.add(ask_user_tool)
            print(f"[Plugin] AskUser tool registered successfully")

            # 5. 加载 MCP tools（复制原始逻辑）
            if mcp_configs:
                from fastmcp.mcp_config import MCPConfig as FastMCPConfig
                validated_mcp_configs = []
                for mcp_config in mcp_configs:
                    try:
                        validated_mcp_configs.append(
                            mcp_config
                            if isinstance(mcp_config, FastMCPConfig)
                            else FastMCPConfig.model_validate(mcp_config)
                        )
                    except Exception as e:
                        from kimi_cli.exception import MCPConfigError
                        raise MCPConfigError(f"Invalid MCP config: {e}") from e
                await toolset.load_mcp_tools(validated_mcp_configs, runtime)

            # 6. 创建 Agent
            return Agent(
                name=agent_spec.name,
                system_prompt=system_prompt,
                toolset=toolset,
                runtime=runtime,
            )
        
        # 替换原始函数
        import kimi_cli.soul.agent
        kimi_cli.soul.agent.load_agent = patched_load_agent


def patch() -> bool:
    """应用 AskUser 工具注册补丁。"""
    patcher = AskUserToolPatch()
    return patcher.apply()
