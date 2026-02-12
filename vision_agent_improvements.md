# Vision Agent 改进说明

## 问题

用户反馈：当任务卡住时，模型没有给出任何指导说点击哪里。

## 改进内容

### 1. 增强反馈分析提示词

**之前：** 只要求返回成功/失败状态

**现在：** 要求模型必须提供：
- `next_action`: 具体的下一步操作指导
  - `action`: 操作类型（click/type/wait/scroll）
  - `target`: 要操作的元素描述或坐标
  - `description`: 操作说明
- `stuck`: 是否卡住
- `stuck_reason`: 卡住的原因

### 2. 显示操作指导

当检测到操作未成功或卡住时，会：
1. 显示模型建议的操作
2. 显示操作说明
3. 如果检测到卡住，显示卡住原因

### 3. 自动执行建议操作

如果检测到卡住且模型提供了 `next_action`，系统会：
1. 自动尝试执行建议的操作
2. 支持的操作类型：
   - `click`: 定位并点击元素
   - `type`: 输入文本
   - `wait`: 等待指定时间
3. 执行后重新验证结果

## 日志输出示例

### 成功情况
```
📊 反馈分析: WPS Office应用已成功打开...
✅ 操作成功确认
```

### 卡住情况（改进后）
```
📊 反馈分析: 当前在WPS主界面，但未创建新表格...
⚠️  操作可能未达到预期
🚨 检测到卡住: 未找到新建按钮或按钮位置不明确
💡 模型建议: click -> 顶部工具栏左侧的"新建"按钮
   点击新建按钮创建新表格
🔄 检测到卡住，尝试执行模型建议的操作...
   操作: click -> 顶部工具栏左侧的"新建"按钮
🖱️  执行建议的点击: (150, 80)
```

## 技术实现

### 提示词改进
```python
prompt = f"""请分析这个屏幕截图，判断操作是否达到了预期结果。

预期结果：{expected_result}

请返回 JSON 格式：
{{
  "success": true/false,
  "next_action": {{
    "action": "click/type/wait/scroll 等",
    "target": "具体要操作的元素描述或坐标",
    "description": "操作说明"
  }},
  "stuck": true/false,
  "stuck_reason": "如果卡住了，说明卡住的原因"
}}

**重要：** 如果操作未成功或卡住了，必须提供具体的 next_action 指导。
"""
```

### 自动执行逻辑
```python
if feedback and feedback.get("stuck") and feedback.get("next_action"):
    next_action = feedback.get("next_action")
    # 根据 action 类型执行相应操作
    if suggested_action == "click":
        # 定位并点击
    elif suggested_action == "type":
        # 输入文本
    elif suggested_action == "wait":
        # 等待
```

## 效果

1. ✅ **模型会主动提供操作指导** - 不再只是描述状态
2. ✅ **自动执行建议操作** - 减少卡住情况
3. ✅ **清晰的日志输出** - 方便调试和追踪
4. ✅ **智能错误恢复** - 根据模型建议自动调整
