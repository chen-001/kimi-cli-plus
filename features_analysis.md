# Kimi-CLI 功能扩展可行性分析报告

## 概述

本文档分析为 kimi-cli 增加5个功能的可行性，包括实现难度、最佳实现形式、对当前架构的影响及潜在风险。

---

## 当前架构概览

### 核心组件

1. **Soul层** (`src/kimi_cli/soul/`)
   - `KimiSoul`: 主代理循环，处理用户输入、调用LLM、执行工具
   - `Runtime`: 运行时配置和共享状态
   - `Approval`: 权限控制系统（含yolo模式）
   - `Context`: 对话历史管理

2. **UI层** (`src/kimi_cli/ui/`)
   - Shell UI: 基于prompt_toolkit的交互式界面
   - `visualize.py`: 实时渲染AI输出、工具调用、权限请求
   - `prompt.py`: 用户输入处理，含底部状态栏

3. **Wire层** (`src/kimi_cli/wire/`)
   - 事件系统：TurnBegin/End, StepBegin, ToolCall, ApprovalRequest等
   - 连接Soul和UI的通信桥梁

4. **工具层** (`src/kimi_cli/tools/`)
   - 文件操作：ReadFile, WriteFile, StrReplaceFile
   - 其他工具：Shell, Search, Web等

---

## 功能1: Plan Mode（计划模式）

### 需求描述
类似Claude Code的plan mode，允许AI先制定计划，用户确认后再执行。

### 可行性分析

**实现难度**: ⭐⭐⭐ 中等

**最佳实现形式**:
1. **新增Agent模式状态**: 在`KimiSoul`中增加`plan_mode`状态标志
2. **Plan工具**: 新增`PlanTool`，AI调用它来输出结构化计划
3. **计划确认流程**: 
   - AI生成计划 → 发送PlanApprovalRequest → 用户确认/修改 → 执行
4. **UI支持**: 在`visualize.py`中渲染计划确认面板

**代码改动点**:
```python
# src/kimi_cli/soul/kimisoul.py
class KimiSoul:
    def __init__(...):
        self._plan_mode = False
        self._pending_plan = None

# src/kimi_cli/wire/types.py  
class PlanApprovalRequest(BaseModel):
    """计划确认请求"""
    plan_steps: list[str]
    # ...
```

**架构影响**: 中等
- 需要扩展Wire事件类型
- 需要修改agent loop以支持"暂停-确认-继续"流程
- 与现有approval系统类似，可以复用模式

**潜在风险**:
1. **用户体验复杂性**: Plan mode增加交互步骤，可能降低效率
2. **计划与实际偏差**: AI制定的计划可能在执行中发现不可行，需要动态调整机制
3. **状态管理**: 需要处理用户中途取消、修改计划等边界情况

**推荐方案**:
- 作为可切换模式（通过`/plan` slash命令）
- 计划以可编辑形式展示（类似现有的approval panel）
- 支持部分执行（选择执行计划中的某些步骤）

---

## 功能2: YOLO模式下保留必要交互

### 需求描述
YOLO模式自动批准权限请求，但当需要用户做选择时仍进行交互。

### 可行性分析

**实现难度**: ⭐⭐ 较低

**当前YOLO实现** (`src/kimi_cli/soul/approval.py`):
```python
async def request(...):
    if self._state.yolo:
        return True  # 直接批准
```

**最佳实现形式**:
1. **区分action类型**: 将action分为"需要批准"和"需要选择"两类
2. **修改Approval.request**: 检查action类型，yolo模式下自动批准某些action，但交互式action仍需用户输入

**代码改动点**:
```python
# src/kimi_cli/soul/approval.py
class Approval:
    # 定义哪些action即使在yolo下也需要交互
    INTERACTIVE_ACTIONS = {"select_option", "choose_branch", ...}
    
    async def request(self, sender, action, description, display=None):
        if self._state.yolo and action not in self.INTERACTIVE_ACTIONS:
            return True
        # 继续正常的请求流程
```

**架构影响**: 很小
- 仅修改`Approval`类，不触碰其他组件
- 保持向后兼容

**潜在风险**:
1. **定义边界复杂**: 区分"危险操作"和"必要交互"的边界可能模糊
2. **用户体验不一致**: 用户可能困惑为什么某些操作在YOLO模式下仍需要交互
3. **安全风险**: 如果interactive actions定义不当，可能绕过YOLO的安全意图

**推荐方案**:
- 添加配置项让用户自定义哪些actions在YOLO下仍需要确认
- 或者采用反向定义：让用户标记"始终需要确认"的actions

---

## 功能3: 回答结束统计信息

### 需求描述
每次AI回答结束后显示：
- TPS (tokens per second)
- 首个token延迟
- 本次回答用时
- API请求次数
- 工具调用次数
- 修改代码行数

### 可行性分析

**实现难度**: ⭐⭐ 较低

**最佳实现形式**:
1. **统计收集器**: 在`KimiSoul`中增加统计信息收集
2. **扩展TurnEnd事件**: 在`TurnEnd`中携带统计信息
3. **UI渲染**: 在`visualize.py`中处理TurnEnd时显示统计

**代码改动点**:
```python
# src/kimi_cli/wire/types.py
class TurnEnd(BaseModel):
    stats: TurnStats | None = None

class TurnStats(BaseModel):
    tps: float
    first_token_latency_ms: int
    total_time_ms: int
    api_requests: int
    tool_calls: int
    lines_added: int
    lines_removed: int

# src/kimi_cli/soul/kimisoul.py
class KimiSoul:
    async def _turn(self, user_message):
        stats_collector = TurnStatsCollector()
        # ... 执行过程中收集统计
        wire_send(TurnEnd(stats=stats_collector.get_stats()))
```

**架构影响**: 小
- 扩展现有事件类型
- 增加统计收集逻辑
- 不破坏现有架构

**潜在风险**:
1. **性能影响**: 统计收集可能轻微影响性能（可忽略）
2. **信息过载**: 统计信息可能干扰用户阅读AI回复
3. **准确性问题**: 
   - TPS计算需要考虑重试、流式输出等复杂情况
   - 代码行数统计（需要追踪文件修改前后的差异）

**推荐方案**:
- 在`TurnEnd`后渲染一个可折叠的统计面板
- 提供配置选项让用户选择显示哪些统计项
- 代码行数统计可以通过在工具层面（WriteFile/StrReplaceFile）hook来实现

---

## 功能4: Session级代码修改状态栏

### 需求描述
底部状态栏或侧边栏显示整个session累积的代码修改情况（各文件增删行数）。

### 可行性分析

**实现难度**: ⭐⭐⭐ 中等

**最佳实现形式**:
1. **修改追踪器**: 在`Runtime`中增加`ModificationTracker`
2. **Hook文件工具**: 在WriteFile/StrReplaceFile执行时通知tracker
3. **实时状态栏**: 在`prompt.py`的底部toolbar中显示

**代码改动点**:
```python
# src/kimi_cli/soul/agent.py
@dataclass
class Runtime:
    modification_tracker: ModificationTracker

class ModificationTracker:
    def __init__(self):
        self.file_changes: dict[str, FileChange] = {}
    
    def record_change(self, path: str, old_text: str, new_text: str):
        # 计算增删行数，累加
        
# src/kimi_cli/tools/file/replace.py
async def __call__(self, params):
    # ... 执行修改后 ...
    self._runtime.modification_tracker.record_change(path, old_text, content)

# src/kimi_cli/ui/shell/prompt.py
def _render_bottom_toolbar(self):
    # 添加修改统计到toolbar
    changes = self._status_provider().modification_summary
    fragments.extend([("", f" +{changes.added}/-{changes.removed}")])
```

**架构影响**: 中等
- 需要修改Runtime以包含tracker
- 需要修改文件工具以上报修改
- 底部toolbar已经是动态更新的，支持此功能

**潜在风险**:
1. **显示空间限制**: 底部toolbar空间有限，难以展示详细信息
2. **实现复杂度**: 需要准确计算每处修改的增删行数（考虑diff算法）
3. **状态持久化**: session恢复时需要恢复修改统计

**推荐方案**:
- **底部状态栏**: 显示简洁摘要（如"+123/-45 lines in 5 files"）
- **侧边栏选项**: 通过`/changes` slash命令弹出详细修改面板
- 支持点击查看完整diff列表

---

## 功能5: Diff View（修改对比视图）

### 需求描述
代码修改时展示具体修改了哪里，提供diff view。

### 可行性分析

**实现难度**: ⭐ 很低

**当前状态分析**:
实际上代码**已经部分支持**此功能！

**已有实现** (`src/kimi_cli/tools/file/replace.py`):
```python
diff_blocks: list[DisplayBlock] = list(
    build_diff_blocks(str(p), original_content, content)
)

# 请求批准时已经显示diff
if not await self._approval.request(
    self.name,
    action,
    f"Edit file `{p}`",
    display=diff_blocks,  # <-- 这里已经传递了diff信息
):
    return ToolRejectedError()
```

**已有实现** (`src/kimi_cli/ui/shell/visualize.py`):
```python
# _ApprovalRequestPanel已经渲染diff
for block in request.display:
    if isinstance(block, DiffDisplayBlock):
        diff_text = format_unified_diff(block.old_text, block.new_text, block.path)
```

**问题分析**:
当前diff只在**approval请求**时显示，如果：
1. YOLO模式下（自动批准）→ 用户看不到diff
2. 用户选择"approve for session"后 → 后续相同action不再显示diff

**最佳实现形式**:
1. **选项1（推荐）**: 在YOLO模式下也显示diff，但不等待用户确认
2. **选项2**: 新增`/diff` slash命令查看最近修改
3. **选项3**: 在工具执行结果中始终包含diff显示

**代码改动点** (选项1):
```python
# src/kimi_cli/ui/shell/visualize.py
class _ToolCallBlock:
    def finish(self, result: ToolReturnValue):
        self._result = result
        # 如果是文件修改工具，渲染diff
        if self._is_file_modification_tool() and result.display:
            # 在console中打印diff（即使在yolo模式下）
            for block in result.display:
                if isinstance(block, DiffDisplayBlock):
                    console.print(format_diff_for_display(block))
```

**架构影响**: 很小
- 复用现有的diff显示逻辑
- 仅需调整UI层的显示时机

**潜在风险**:
1. **输出冗长**: 大量小修改可能导致输出过多diff
2. **性能**: 大文件的diff计算可能影响性能
3. **用户体验**: 需要平衡信息量和可读性

**推荐方案**:
- **默认开启**: 在YOLO模式下也显示简洁的diff摘要
- **可配置**: 添加`--diff-on-yolo`配置选项
- **智能截断**: 大文件的diff只显示关键部分

---

## 总结与优先级建议

| 功能 | 实现难度 | 架构影响 | 推荐优先级 | 关键改动文件 |
|------|----------|----------|------------|--------------|
| 功能5: Diff View | ⭐ | 很小 | **P0** | `visualize.py` |
| 功能3: 统计信息 | ⭐⭐ | 小 | **P1** | `kimisoul.py`, `types.py`, `visualize.py` |
| 功能2: YOLO交互 | ⭐⭐ | 很小 | **P1** | `approval.py` |
| 功能4: 修改状态栏 | ⭐⭐⭐ | 中等 | **P2** | `agent.py`, `replace.py`, `write.py`, `prompt.py` |
| 功能1: Plan Mode | ⭐⭐⭐ | 中等 | **P2** | `kimisoul.py`, `types.py`, `visualize.py`, 新增plan工具 |

### 实施建议

1. **先实现功能5**: 基础已存在，改动最小，用户体验提升明显
2. **功能3与功能4结合**: 统计信息和修改追踪可以共用部分基础设施
3. **功能1最后实现**: 需要最多的设计和测试，影响核心agent loop
4. **功能2需要产品决策**: 需要明确定义"必要交互"的边界

### 长期架构考虑

1. **事件系统扩展**: Wire事件类型可能需要版本管理，以支持向后兼容
2. **配置系统增强**: 用户可能需要更细粒度的配置选项
3. **可插拔UI**: 当前分析基于Shell UI，未来可能需要支持其他UI（GUI/Web）
