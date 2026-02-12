# Cursor IDE 智能监控使用指南

## 功能概述

智能监控系统不仅检测屏幕内容是否变化，还会：

1. **理解上下文**：分析用户在做什么（查看历史记录、等待响应等）
2. **内容分析**：理解 Cursor 输出的内容和对话进展
3. **智能判断**：区分"正在思考"和"真的卡住"
4. **详细报告**：通过 WhatsApp 发送完整的分析报告

## 快速开始

### 启动监控

```bash
# 方式 1: 直接启动
bash /Users/oscar/moltbot/cursor_smart_monitor.sh start

# 方式 2: 使用命令脚本
bash /Users/oscar/moltbot/openclaw_monitor_command.sh start
```

### 停止监控

```bash
# 方式 1: 使用命令脚本
bash /Users/oscar/moltbot/openclaw_monitor_command.sh stop

# 方式 2: 直接停止进程
pkill -f cursor_smart_monitor.sh
```

### 查看状态

```bash
bash /Users/oscar/moltbot/openclaw_monitor_command.sh status
```

## 在 OpenClaw 中使用

### 方式 1: 通过 WhatsApp 命令（推荐）

在 WhatsApp 中发送：
- `/monitor-start` - 启动监控
- `/monitor-stop` - 停止监控
- `/monitor-status` - 查看状态

（需要先配置 OpenClaw 的命令处理）

### 方式 2: 通过 Gateway RPC

```bash
# 启动
cd /Users/oscar/moltbot/openclaw && \
pnpm openclaw gateway call exec \
  --params '{"command":"bash /Users/oscar/moltbot/openclaw_monitor_command.sh start"}'

# 停止
cd /Users/oscar/moltbot/openclaw && \
pnpm openclaw gateway call exec \
  --params '{"command":"bash /Users/oscar/moltbot/openclaw_monitor_command.sh stop"}'
```

## 智能分析功能

### 1. 状态理解

监控系统会分析：
- **用户在做什么**：查看历史记录、等待响应、输入问题、查看代码等
- **AI 在做什么**：正在思考、正在生成代码、已完成响应、等待用户输入等
- **对话阶段**：初始阶段、进行中、已完成、卡住等

### 2. 内容分析

- 用户最近的问题
- AI 的回复内容（如果可见）
- 是否有错误信息或警告
- 代码生成是否完成

### 3. 问题检测

- **区分"正在思考"和"真的卡住"**
- 检测思路偏差（AI 理解错误、方向不对等）
- 判断是否需要人工干预

### 4. 上下文理解

- 如果用户在往上翻聊天记录 → 可能是在回顾之前的对话
- 如果 AI 长时间没有新输出 → 可能真的卡住了
- 当前任务是否正常进行

## 通知机制

### 触发条件

1. **检测到紧急关键词**：
   - "卡住"、"错误"、"失败"、"超时"、"异常"
   - "无法"、"需要人工干预"、"思路偏差"、"理解错误"

2. **状态持续异常**：
   - 连续 2 次检测到问题
   - 距离上次通知超过 5 分钟（避免频繁通知）

### 通知内容

通知包含：
- 详细的状态分析
- 用户和 AI 的当前活动
- 问题检测结果
- 建议操作

## 配置选项

### 环境变量

```bash
# 监控间隔（秒）
export CURSOR_SMART_MONITOR_INTERVAL=15

# WhatsApp 目标号码
export CURSOR_SMART_MONITOR_WHATSAPP="+8613701223827"
```

### 修改脚本配置

编辑 `/Users/oscar/moltbot/cursor_smart_monitor.sh`：

```bash
INTERVAL=${CURSOR_SMART_MONITOR_INTERVAL:-15}  # 默认 15 秒
WHATSAPP_TARGET=${CURSOR_SMART_MONITOR_WHATSAPP:-"+8613701223827"}
```

## 日志查看

### 实时日志

```bash
tail -f ~/.openclaw/cursor_smart_monitor.log
```

### 查看最近日志

```bash
tail -50 ~/.openclaw/cursor_smart_monitor.log
```

## 与旧版监控的区别

| 功能 | 旧版监控 | 智能监控 |
|------|---------|---------|
| 检测方式 | 图片哈希比较 | AI 内容分析 |
| 理解能力 | ❌ 无 | ✅ 理解上下文 |
| 状态判断 | 简单（变化/不变） | 智能（思考/卡住/正常） |
| 通知内容 | 简单提示 | 详细分析报告 |
| 成本 | 低（仅截图） | 中（AI 分析，但使用免费模型） |

## 技术实现

### AI 模型

使用 **302 平台的 GLM-4.6v-flash**：
- ✅ 免费
- ✅ 支持图片输入
- ✅ 响应速度快（2-3 秒）
- ✅ 中文支持好

### 分析流程

```
截图 → AI 分析 → 状态判断 → 问题检测 → 通知（如需要）
```

### 状态保存

- 分析结果保存在：`~/.openclaw/cursor_monitor_state/last_analysis.txt`
- 截图保存在：`~/.openclaw/cursor_screenshots/`

## 故障排除

### 监控未启动

1. 检查 Cursor 是否运行
2. 检查权限（屏幕录制权限）
3. 查看日志：`tail -f ~/.openclaw/cursor_smart_monitor.log`

### 分析失败

1. 检查网络连接（需要访问 302 平台 API）
2. 检查 API Key 是否有效
3. 查看日志中的错误信息

### 通知未发送

1. 检查 OpenClaw Gateway 是否运行
2. 检查 WhatsApp 通道配置
3. 查看 Gateway 日志

## 下一步改进

1. **集成到 OpenClaw 命令系统**：添加 `/monitor-start` 等命令
2. **更智能的判断**：学习用户的工作模式
3. **多窗口支持**：监控多个 Cursor 窗口
4. **历史记录分析**：分析完整的对话历史
