# OpenClaw 卡住时的重启方案

## 🚨 快速重启（推荐，最简单）

```bash
# 一键重启命令
launchctl unload ~/Library/LaunchAgents/ai.openclaw.gateway.plist && sleep 3 && launchctl load ~/Library/LaunchAgents/ai.openclaw.gateway.plist && sleep 5 && tail -20 ~/.openclaw/logs/gateway.log
```

## 📋 详细步骤方案

### 方案 1：优雅重启（推荐）

```bash
# 步骤 1：停止 Gateway 服务
launchctl unload ~/Library/LaunchAgents/ai.openclaw.gateway.plist

# 步骤 2：等待 3 秒
sleep 3

# 步骤 3：重新启动
launchctl load ~/Library/LaunchAgents/ai.openclaw.gateway.plist

# 步骤 4：检查状态（等待 5 秒后）
sleep 5
tail -20 ~/.openclaw/logs/gateway.log
```

### 方案 2：强制重启（如果方案 1 不行）

```bash
# 步骤 1：强制杀死所有 OpenClaw 进程
pkill -9 -f openclaw-gateway
pkill -9 -f openclaw

# 步骤 2：等待 2 秒
sleep 2

# 步骤 3：重新启动服务
launchctl load ~/Library/LaunchAgents/ai.openclaw.gateway.plist

# 步骤 4：检查状态
sleep 5
ps aux | grep openclaw | grep -v grep
tail -20 ~/.openclaw/logs/gateway.log
```

### 方案 3：完全重启（最彻底，清理所有）

```bash
# 步骤 1：停止服务
launchctl unload ~/Library/LaunchAgents/ai.openclaw.gateway.plist

# 步骤 2：杀死所有相关进程
pkill -9 -f openclaw
pkill -9 -f gateway

# 步骤 3：清理锁文件（如果有）
rm -f ~/.openclaw/.gateway.lock
rm -f /tmp/openclaw-*.lock

# 步骤 4：等待端口释放
sleep 5

# 步骤 5：重新启动
launchctl load ~/Library/LaunchAgents/ai.openclaw.gateway.plist

# 步骤 6：验证
sleep 5
curl -s http://127.0.0.1:18789/health 2>/dev/null || echo "Gateway 启动中..."
tail -30 ~/.openclaw/logs/gateway.log
```

### 方案 4：手动启动 Gateway（用于调试）

如果服务启动有问题，可以手动启动查看详细输出：

```bash
cd /Users/oscar/moltbot/openclaw
source ~/.nvm/nvm.sh && nvm use 22
pnpm gateway:watch
```

按 `Ctrl+C` 停止手动启动的 Gateway。

## 🔍 检查 Gateway 是否正常

### 检查进程
```bash
ps aux | grep openclaw-gateway | grep -v grep
```

### 检查端口
```bash
lsof -i :18789
```

### 检查日志
```bash
tail -f ~/.openclaw/logs/gateway.log
```

### 检查 Web UI
```bash
open http://127.0.0.1:18789/
```

### 检查服务状态
```bash
launchctl list | grep openclaw
```

## 🐛 诊断卡住原因

### 1. 检查是否有长时间运行的 agent 任务
```bash
grep -E "agent.wait|timeout" ~/.openclaw/logs/gateway.log | tail -10
```

### 2. 检查错误日志
```bash
tail -50 ~/.openclaw/logs/gateway.err.log
```

### 3. 检查最近的错误
```bash
tail -100 ~/.openclaw/logs/gateway.log | grep -E "error|Error|ERROR|failed|Failed" | tail -20
```

## 📝 使用建议

1. **平时卡住**：用方案 1（优雅重启）
2. **方案 1 不行**：用方案 2（强制重启）
3. **还是不行**：用方案 3（完全重启）
4. **需要调试**：用方案 4（手动启动）

## ⚡ 一键重启脚本

保存以下内容到 `~/restart_openclaw.sh`：

```bash
#!/bin/bash
echo "🔄 正在重启 OpenClaw Gateway..."
launchctl unload ~/Library/LaunchAgents/ai.openclaw.gateway.plist
sleep 3
pkill -9 -f openclaw-gateway 2>/dev/null
sleep 2
launchctl load ~/Library/LaunchAgents/ai.openclaw.gateway.plist
sleep 5
echo "✅ 重启完成！"
echo ""
echo "📊 检查状态："
ps aux | grep openclaw-gateway | grep -v grep && echo "✅ Gateway 进程运行中" || echo "❌ Gateway 未运行"
echo ""
echo "📝 最新日志："
tail -10 ~/.openclaw/logs/gateway.log
```

然后运行：
```bash
chmod +x ~/restart_openclaw.sh
~/restart_openclaw.sh
```
