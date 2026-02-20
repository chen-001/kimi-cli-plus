向用户提问或请求选择。即使在YOLO模式下也会暂停等待用户回复。

当用户指令不够明确、需要补充信息、或需要用户做选择时使用此工具。

**参数说明：**
- `question` (string, required): 要问用户的问题
- `options` (string[], optional): 可选的选项列表。提供后用户必须从选项中选择
- `require_input` (boolean, optional): 是否需要用户输入文字。默认 true

**使用示例：**

1. 简单询问（自由输入）：
```json
{
  "question": "请指定要优化的文件路径"
}
```

2. 多选项选择：
```json
{
  "question": "请选择优化方向",
  "options": ["提速", "省内存", "增强可读性"]
}
```

3. 多选项选择（仅需确认）：
```json
{
  "question": "确认删除此文件？",
  "options": ["确认删除", "取消"],
  "require_input": false
}
```

**注意事项：**
- 如果用户取消回答，会返回 `cancelled=true`，当前任务应该停止
- 如果提供了 `options`，用户必须从选项中选择
- 如果 `require_input=false`，必须提供 `options`，否则工具无法正常工作
