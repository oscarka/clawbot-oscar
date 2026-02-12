# OpenClaw 卡顿问题 - 不重启的解决方案

## 🎯 方案 1：使用命令停止卡住的任务（最简单）

### 在 TUI 或 WebChat 中发送：

```
/stop
```
或
```
/abort
```

这会：
- 停止当前运行的 agent 任务
- 清理会话队列
- 停止所有子 agent

### 重置会话（清除历史，重新开始）

```
/new
```
或
```
/reset
```

### 停止所有子 agent

```
/subagents stop all
```

## 🔧 方案 2：通过 CLI 命令操作

### 重置主会话

```bash
cd /Users/oscar/moltbot/openclaw
source ~/.nvm/nvm.sh && nvm use 22

# 连接到 Gateway 并重置会话
pnpm openclaw agent --message "/reset" --session main
```

### 查看当前活跃的会话

```bash
pnpm openclaw agent --message "/status" --session main
```

## 🌐 方案 3：通过 Web UI 操作

1. 打开 Web UI：http://127.0.0.1:18789/
2. 在聊天界面输入：
   - `/stop` - 停止当前任务
   - `/new` - 重置会话
   - `/abort` - 强制中止

## 📡 方案 4：通过 Gateway WebSocket API（高级）

如果你有 WebSocket 客户端，可以发送：

```javascript
// 中止当前会话的任务
{
  "method": "chat.abort",
  "params": {
    "sessionKey": "agent:main:main"
  }
}

// 重置会话
{
  "method": "sessions.reset",
  "params": {
    "key": "agent:main:main"
  }
}
```

## 🗑️ 方案 5：清理卡住的会话文件

### 查看会话文件大小（找出异常大的文件）

```bash
ls -lh ~/.openclaw/agents/main/sessions/*.jsonl | sort -k5 -hr | head -5
```

### 备份并清理异常大的会话文件

```bash
# 备份
cp ~/.openclaw/agents/main/sessions/sessions.json ~/.openclaw/agents/main/sessions/sessions.json.backup

# 查看当前会话状态
cat ~/.openclaw/agents/main/sessions/sessions.json | jq .
```

### 手动清理特定会话（谨慎操作）

```bash
# 先备份
cp ~/.openclaw/agents/main/sessions/sessions.json ~/.openclaw/agents/main/sessions/sessions.json.backup.$(date +%Y%m%d_%H%M%S)

# 编辑会话文件（移除卡住的会话）
# 注意：这需要你知道哪个会话卡住了
```

## 🔍 方案 6：诊断并清理队列

### 检查是否有卡住的任务

```bash
# 查看最近的超时记录
grep -E "agent.wait|timeout|abort" ~/.openclaw/logs/gateway.log | tail -20

# 查看错误日志
tail -50 ~/.openclaw/logs/gateway.err.log | grep -E "timeout|failed|error"
```

### 清理临时文件和锁

```bash
# 清理可能的锁文件
rm -f ~/.openclaw/.gateway.lock
rm -f /tmp/openclaw-*.lock

# 清理临时会话数据（谨慎）
# rm -f ~/.openclaw/agents/main/sessions/*.jsonl
```

## ⚙️ 方案 7：调整配置优化性能（不重启，下次生效）

### 降低超时时间（避免长时间卡住）

编辑 `~/.openclaw/openclaw.json`：

```json
{
  "agents": {
    "defaults": {
      "timeoutSeconds": 120,  // 从 600 秒降到 120 秒（2分钟）
      "maxConcurrent": 1      // 从 4 降到 1，避免并发冲突
    }
  }
}
```

然后发送 `/restart` 命令（如果启用了）或重启 Gateway。

### 禁用慢速功能

```json
{
  "tools": {
    "web": {
      "search": {
        "enabled": false  // 禁用网络搜索，避免 API 限流
      }
    }
  },
  "hooks": {
    "internal": {
      "entries": {
        "session-memory": {
          "enabled": false  // 禁用内存 hook，避免 embeddings 超时
        }
      }
    }
  }
}
```

## 🚨 方案 8：强制清理进程（不重启 Gateway）

### 只杀死卡住的 agent 进程

```bash
# 查找可能的卡住进程
ps aux | grep -E "node.*agent|pi-agent" | grep -v grep

# 如果发现有卡住的进程，可以杀死（谨慎）
# pkill -9 -f "pi-agent"
```

## 📋 推荐使用顺序

1. **首先尝试**：在聊天界面发送 `/stop` 或 `/abort`
2. **如果不行**：发送 `/new` 重置会话
3. **还是卡**：发送 `/subagents stop all` 停止所有子任务
4. **检查诊断**：运行诊断命令查看具体问题
5. **最后手段**：清理会话文件或重启 Gateway

## 🎯 快速命令参考

```bash
# 在 TUI/WebChat 中：
/stop          # 停止当前任务
/abort         # 强制中止
/new           # 重置会话
/reset         # 重置会话（同 /new）
/subagents stop all  # 停止所有子 agent

# 通过 CLI：
pnpm openclaw agent --message "/stop" --session main
pnpm openclaw agent --message "/new" --session main

# 检查状态：
tail -f ~/.openclaw/logs/gateway.log | grep -E "agent|timeout|error"
```

## 💡 预防措施

1. **设置合理的超时**：`timeoutSeconds: 120`（2分钟）
2. **降低并发**：`maxConcurrent: 1`
3. **禁用慢速功能**：如 web search、session-memory
4. **定期清理**：删除过大的会话历史文件
5. **监控日志**：定期检查是否有超时或错误
