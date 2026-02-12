# 成熟方案测试指南

## 快速开始

### 方式 1: 运行测试脚本（推荐）

```bash
# 运行测试（会自动更新状态）
python3 /Users/oscar/moltbot/test_mature_solutions.py
```

### 方式 2: 监控状态（另一个终端）

```bash
# 在另一个终端窗口运行，实时显示状态
/Users/oscar/moltbot/monitor_status.sh
```

### 方式 3: 查看状态文件

```bash
# 随时查看当前状态
cat /tmp/vision_agent_status.txt

# 查看完整日志
tail -f /tmp/vision_agent_status.log
```

## 状态说明

### 状态类型

- **进行中** 🟢 - 任务正在执行
- **卡住了** 🟡 - 检测到问题，可能卡住
- **中断了** 🔴 - 任务失败或中断
- **完成** 🔵 - 任务成功完成

### 状态文件位置

- **状态文件**: `/tmp/vision_agent_status.txt` - 当前状态（显眼位置）
- **日志文件**: `/tmp/vision_agent_status.log` - 完整日志

## 测试内容

1. **Peekaboo Agent 模式** - 检查是否支持 Agent
2. **OpenClaw + Peekaboo** - 检查集成情况
3. **Claude Computer Use** - 检查 API 可用性
4. **实际任务执行** - 测试飞书发送文件任务

## 通知

测试过程中会发送 macOS 通知：
- 开始测试
- 关键状态变化
- 完成/失败

## 建议

1. **开两个终端**：
   - 终端1: 运行测试脚本
   - 终端2: 运行监控脚本，实时查看状态

2. **或者**：
   - 运行测试脚本
   - 随时用 `cat /tmp/vision_agent_status.txt` 查看状态

3. **如果卡住**：
   - 查看日志: `tail -f /tmp/vision_agent_status.log`
   - 检查状态文件: `cat /tmp/vision_agent_status.txt`
