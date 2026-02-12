# Cursor 智能监控快速开始

## 功能特点

✅ **智能理解**：不仅检测变化，还理解你在做什么
- 查看历史记录
- 等待 AI 响应
- 输入问题
- 查看代码

✅ **内容分析**：理解 Cursor 输出的内容和对话进展

✅ **智能判断**：区分"正在思考"和"真的卡住"

✅ **详细报告**：通过 WhatsApp 发送完整的分析报告

## 快速启动

### 方式 1: 直接启动（推荐）

```bash
bash /Users/oscar/moltbot/cursor_smart_monitor.sh start
```

### 方式 2: 使用命令脚本

```bash
# 启动
bash /Users/oscar/moltbot/openclaw_monitor_command.sh start

# 停止
bash /Users/oscar/moltbot/openclaw_monitor_command.sh stop

# 查看状态
bash /Users/oscar/moltbot/openclaw_monitor_command.sh status
```

### 方式 3: 后台运行

```bash
nohup bash /Users/oscar/moltbot/cursor_smart_monitor.sh start > /dev/null 2>&1 &
```

## 在 WhatsApp 中使用（未来功能）

发送以下命令：
- `/monitor-start` - 启动监控
- `/monitor-stop` - 停止监控
- `/monitor-status` - 查看状态

（需要先配置 OpenClaw 命令处理）

## 监控逻辑

### 智能分析流程

```
截图 → AI 分析 → 理解上下文 → 判断状态 → 检测问题 → 通知（如需要）
```

### 分析内容

1. **当前状态判断**
   - 用户在做什么？
   - AI 在做什么？
   - 对话进行到哪个阶段？

2. **内容分析**
   - 用户最近的问题
   - AI 的回复内容
   - 是否有错误信息

3. **问题检测**
   - 是否真的卡住了？
   - 是否有思路偏差？
   - 是否需要人工干预？

4. **上下文理解**
   - 如果用户在往上翻聊天记录 → 可能是在回顾
   - 如果 AI 长时间没有新输出 → 可能真的卡住了

### 通知触发条件

- 检测到紧急关键词（"卡住"、"错误"、"失败"等）
- 状态持续异常（连续 2 次检测到问题）
- 距离上次通知超过 5 分钟（避免频繁通知）

## 查看日志

```bash
# 实时日志
tail -f ~/.openclaw/cursor_smart_monitor.log

# 最近日志
tail -50 ~/.openclaw/cursor_smart_monitor.log
```

## 配置

### 修改监控间隔

```bash
export CURSOR_SMART_MONITOR_INTERVAL=20  # 改为 20 秒
bash /Users/oscar/moltbot/cursor_smart_monitor.sh start
```

### 修改 WhatsApp 目标

```bash
export CURSOR_SMART_MONITOR_WHATSAPP="+8613701223827"
```

## 与旧版监控的区别

| 功能 | 旧版监控 | 智能监控 |
|------|---------|---------|
| 检测方式 | 图片哈希比较 | AI 内容分析 |
| 理解能力 | ❌ 无 | ✅ 理解上下文 |
| 状态判断 | 简单（变化/不变） | 智能（思考/卡住/正常） |
| 通知内容 | 简单提示 | 详细分析报告 |
| 成本 | 低（仅截图） | 中（AI 分析，但使用免费模型） |

## 故障排除

### 监控未启动

1. 检查 Cursor 是否运行
2. 检查权限（屏幕录制权限）
3. 查看日志：`tail -f ~/.openclaw/cursor_smart_monitor.log`

### 分析失败

1. 检查网络连接（需要访问 302 平台 API）
2. 检查 API Key 是否有效
3. 查看日志中的错误信息

## 下一步

1. 集成到 OpenClaw 命令系统（添加 `/monitor-start` 等命令）
2. 更智能的判断（学习用户的工作模式）
3. 多窗口支持（监控多个 Cursor 窗口）
