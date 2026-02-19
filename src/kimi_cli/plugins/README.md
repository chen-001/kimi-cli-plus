# Kimi CLI 用户插件

用户自定义的可插拔功能，不影响官方代码，可随官方更新保留。

## 包含功能

### ✅ 功能2: YOLO模式下的用户交互 (AskUser)
- 在YOLO（自动批准）模式下，AI仍可向用户提问或请求选择
- 支持选项按钮和自由输入两种模式
- 询问和回复保留在对话历史中
- 用户取消时停止当前任务

### ✅ 功能3: 回答结束统计信息
每次AI回答后显示：
- ⏱️ 首token延迟
- ⏳ 总用时
- ⚡ TPS (tokens per second)
- 🌐 API请求次数
- 🔧 工具调用次数
- 📝 代码修改行数 (+added/-removed)

### ✅ 功能4: Session级修改状态栏
- 底部状态栏显示累积代码修改
- 格式: `+123/-45 (5 files)`
- 实时更新，跨Turn累积

### ✅ 功能5: 持久Diff展示
- 文件修改后显示带颜色的diff视图
- 类似GitHub的diff样式（红绿高亮）
- 不受YOLO模式影响，始终可见

---

## 安装方法

### 方法1: 使用Wrapper脚本（推荐）

```bash
# 创建别名
echo 'alias kimi="python -m kimi_cli.plugins.entry"' >> ~/.bashrc
# 或 ~/.zshrc

source ~/.bashrc  # 或 ~/.zshrc
```

### 方法2: 直接运行

```bash
python -m kimi_cli.plugins.entry
```

### 方法3: 修改启动器（Linux/Mac）

如果你使用`kimi`命令：

```bash
# 找到kimi-cli入口
which kimi
# 编辑该文件，在开头添加:
from kimi_cli.plugins import apply_all_patches
apply_all_patches()
```

---

## 更新官方版本时

由于所有代码都在`plugins/`目录下，不影响官方代码：

```bash
# 1. 更新官方版本
uv tool upgrade kimi-cli

# 2. 检查插件兼容性
python -c "from kimi_cli.plugins.utils.version_check import check_compatibility; print(check_compatibility('1.0.0', '0.70.0'))"

# 3. 如有问题，更新插件代码（保留你的plugins目录）
# 插件目录在: src/kimi_cli/plugins/

# 4. 正常使用
kimi
```

---

## 配置选项

### 禁用特定功能

编辑 `__init__.py` 中的 `apply_all_patches()`:

```python
def apply_all_patches():
    # 只启用需要的功能
    from .patches import visualize_patch, kimisoul_patch
    visualize_patch.patch()  # 功能5
    kimisoul_patch.patch()   # 功能3
    # mod_tracker_patch.patch()  # 功能4 - 禁用
    # approval_patch.patch()     # 功能2 - 禁用
```

### 自定义统计信息显示

编辑 `patches/kimisoul_patch.py` 中的 `TurnStats.format_display()`:

```python
def format_display(self) -> str:
    # 自定义显示格式
    return f"用时{self.total_time_ms//1000}s | {self.tool_calls}工具"
```

---

## 文件结构

```
plugins/
├── __init__.py           # 主入口，应用所有补丁
├── entry.py              # 命令行入口
├── README.md             # 本文档
├── core/                 # 补丁基础设施
│   ├── __init__.py
│   └── patch_base.py     # Patch基类和工具
├── patches/              # 功能补丁
│   ├── __init__.py
│   ├── approval_patch.py     # 功能2: AskUser
│   ├── visualize_patch.py    # 功能5: Diff展示
│   ├── kimisoul_patch.py     # 功能3: 统计信息
│   └── mod_tracker_patch.py  # 功能4: 修改追踪
├── tools/                # 新增工具
│   ├── __init__.py
│   └── ask_user.py       # AskUser工具
└── utils/                # 工具函数
    ├── __init__.py
    └── version_check.py  # 版本检查
```

---

## 兼容性

- **插件版本**: 1.0.0
- **最低kimi-cli版本**: 0.70.0
- **测试版本**: 0.70.0+

---

## 故障排除

### 插件未生效

```bash
# 检查插件是否加载
python -c "from kimi_cli.plugins import get_applied_patches; print(get_applied_patches())"
# 应输出: ['approval', 'visualize', 'kimisoul', 'mod_tracker']
```

### 版本不兼容

```bash
# 检查版本
python -c "from kimi_cli.plugins.utils.version_check import check_compatibility, get_kimi_version; print(get_kimi_version())"
```

### 恢复原版

```bash
# 临时禁用插件，直接使用原版
python -m kimi_cli.cli
```

---

## 开发说明

### 添加新补丁

1. 在 `patches/` 创建新文件
2. 继承 `PatchBase` 类
3. 实现 `apply()` 方法
4. 在 `__init__.py` 中调用

```python
# patches/my_patch.py
from kimi_cli.plugins.core import PatchBase

class MyPatch(PatchBase):
    def apply(self):
        # 你的补丁代码
        pass

def patch():
    return MyPatch().apply()
```

### 调试

```bash
# 启用调试日志
export KIMI_DEBUG=1
python -m kimi_cli.plugins.entry
```

---

## 许可

与kimi-cli保持一致。
