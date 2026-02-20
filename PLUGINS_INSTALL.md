# Kimi CLI 用户插件安装指南

## 快速开始

### 1. 确认插件文件已存在

检查以下文件是否存在：
```
src/kimi_cli/plugins/           # 插件目录
kimi-with-plugins               # 启动脚本
```

### 2. 启动带插件的kimi-cli-plus

**方法A: 直接使用wrapper脚本**
```bash
./kimi-with-plugins
```

**方法B: 使用Python模块**
```bash
python -m kimi_cli.plugins.entry
```

**方法C: 设置别名（推荐）**
```bash
# 添加到 ~/.bashrc 或 ~/.zshrc
echo 'alias kimi="/path/to/kimi-cli-plus/kimi-with-plugins"' >> ~/.bashrc
source ~/.bashrc

# 然后直接使用
kimi
```

### 3. 验证插件是否生效

启动后会看到类似输出：
```
[Plugin] approval_inquiry applied successfully
[Plugin] visualize_diff_display applied successfully
[Plugin] kimisoul_stats applied successfully
[Plugin] mod_tracker applied successfully
```

## 功能说明

### 功能2: YOLO模式下的用户交互 (AskUser)

当AI需要向你确认信息时，即使在YOLO模式下也会暂停等待你的回复。

**使用方式**: 当AI需要询问时，会自动显示交互面板：
- 有选项时：显示选项列表，用方向键选择
- 无选项时：提示输入回复

**取消行为**: 按Esc或选择"取消"会停止当前任务。

### 功能3: 回答结束统计信息

每次AI回答结束后，会在对话下方显示统计面板：
```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ 📊 本次回答统计                         ┃
┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┫
┃ ⏱️ 首token: 500ms | ⏳ 总用时: 15.234s  ┃
┃ ⚡ TPS: 45.2 | 🌐 API: 3 | 🔧 工具: 5    ┃
┃ 📝 代码: +50/-20                        ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```

### 功能4: 修改状态栏

底部状态栏会显示累积修改：
```
14:32  agent (kimi-latest)   +123/-45 (5 files)   context: 35.2%
```

显示内容：
- `+123`: 总共增加123行
- `-45`: 总共删除45行  
- `(5 files)`: 修改了5个文件

### 功能5: 持久Diff展示

文件修改后会显示带颜色的diff：
```
📄 StrReplaceFile - 文件修改详情

src/example.py
─────────────────────────────────────────────
@@ -10,7 +10,7 @@
  def old_function():
-    print("old")
+    print("new")
      return True
─────────────────────────────────────────────
```

绿色(`+`)表示新增，红色(`-`)表示删除。

## 更新kimi-cli-plus时

由于插件代码完全独立于官方代码，更新官方版本非常简单：

```bash
# 1. 更新官方版本
uv tool upgrade kimi-cli-plus

# 2. 继续使用带插件的版本
./kimi-with-plugins
```

**注意**: 如果官方版本有大的架构变化，插件可能需要更新。

## 禁用特定功能

编辑 `src/kimi_cli/plugins/__init__.py`：

```python
def apply_all_patches():
    # 注释掉不想启用的功能
    
    # 功能2: AskUser（YOLO交互）
    from .patches import approval_patch
    approval_patch.patch()
    
    # 功能5: Diff持久展示
    from .patches import visualize_patch
    visualize_patch.patch()
    
    # 功能3: 统计信息
    from .patches import kimisoul_patch
    kimisoul_patch.patch()
    
    # 功能4: 修改状态栏
    # from .patches import mod_tracker_patch  # 禁用这行
    # mod_tracker_patch.patch()
```

## 故障排除

### 问题1: 插件未生效

**现象**: 启动时没有`[Plugin] ... applied successfully`消息

**解决**:
```bash
# 检查Python路径
cd /path/to/kimi-cli-plus
python -c "import sys; print(sys.path)"

# 确保是从正确目录启动
python -m kimi_cli.plugins.entry
```

### 问题2: 版本不兼容警告

**现象**: 启动时出现版本警告

**解决**: 
- 警告不影响基本使用
- 如果功能异常，可能需要更新插件代码

### 问题3: Diff没有颜色

**现象**: diff显示为纯文本，没有红绿高亮

**解决**: 检查终端是否支持颜色输出，尝试：
```bash
export TERM=xterm-256color
./kimi-with-plugins
```

### 问题4: 状态栏不显示修改统计

**现象**: 底部状态栏没有`+x/-y`显示

**解决**: 
1. 确认`mod_tracker_patch`已应用
2. 需要至少一次文件修改后才会显示
3. 修改文件后状态栏会更新

## 卸载插件

如果需要完全移除插件功能：

```bash
# 方法1: 直接使用原版启动命令
python -m kimi_cli.cli

# 方法2: 临时禁用（单次）
KIMI_NO_PLUGINS=1 ./kimi-with-plugins  # 如果支持

# 方法3: 删除插件目录（永久）
rm -rf src/kimi_cli/plugins
rm kimi-with-plugins
```

## 自定义修改

### 修改统计信息显示格式

编辑 `src/kimi_cli/plugins/patches/kimisoul_patch.py`：

```python
# 在 TurnStats.format_display() 方法中
parts = []
parts.append(f"用时: {self.total_time_ms//1000}s")  # 简化为秒
parts.append(f"工具: {self.tool_calls}")
# 删除不需要的统计项
# parts.append(f"TPS: {self.tps}")
return " | ".join(parts)
```

### 修改状态栏位置

编辑 `src/kimi_cli/plugins/patches/mod_tracker_patch.py`：

```python
# 在 _patch_prompt_render() 方法中
# 修改插入位置来改变显示顺序
```

## 开发者信息

### 插件架构

```
plugins/
├── core/           # 补丁基础设施
├── patches/        # 功能补丁（每个功能一个文件）
├── tools/          # 新增工具
└── utils/          # 工具函数
```

### 添加新功能

1. 在 `patches/` 创建新文件
2. 继承 `PatchBase` 类
3. 实现 `apply()` 方法
4. 在 `__init__.py` 中导入并调用

参考现有补丁的实现方式。

## 反馈与支持

如有问题，请检查：
1. 确认kimi-cli-plus版本 >= 0.70.0
2. 检查Python版本 >= 3.9
3. 查看启动时的插件加载日志
