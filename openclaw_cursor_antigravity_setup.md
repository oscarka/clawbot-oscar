# 利用 Cursor 和 Google Antigravity 账号配置 OpenClaw

## 概述

OpenClaw 支持通过 CLI backends 使用本地 AI CLI 工具，这意味着你可以利用已有的 Cursor 和 Google Antigravity 账号，避免 API 限流和成本问题。

## 方案一：使用 Claude CLI（如果 Cursor 有 CLI）

### 前提条件

1. **检查 Cursor 是否提供 CLI**
   - Cursor 通常基于 Claude，如果有 CLI 工具，可以直接使用
   - 检查是否有 `cursor` 或 `claude` 命令

2. **检查 Claude Code CLI**
   - OpenClaw 内置支持 `claude-cli`
   - 如果已安装 Claude Code CLI，可以直接使用

### 配置步骤

#### 步骤 1：找到 CLI 命令路径

```bash
# 检查 Claude CLI
which claude

# 检查 Cursor CLI（如果有）
which cursor

# 如果找不到，检查常见位置
ls -la /opt/homebrew/bin/claude
ls -la /usr/local/bin/claude
ls -la ~/.cursor/bin/cursor
```

#### 步骤 2：配置 OpenClaw

编辑 `~/.openclaw/openclaw.json`，添加 CLI backend 配置：

```json
{
  "agents": {
    "defaults": {
      "cliBackends": {
        "claude-cli": {
          "command": "/opt/homebrew/bin/claude"
        },
        "cursor-cli": {
          "command": "/path/to/cursor",
          "args": ["--json"],
          "output": "json",
          "modelArg": "--model",
          "sessionArg": "--session",
          "sessionMode": "existing"
        }
      },
      "model": {
        "primary": "claude-cli/opus-4.5",
        "fallbacks": [
          "anthropic/claude-opus-4-5"
        ]
      },
      "models": {
        "claude-cli/opus-4.5": { "alias": "Cursor Opus" },
        "claude-cli/sonnet-4.5": { "alias": "Cursor Sonnet" },
        "anthropic/claude-opus-4-5": { "alias": "API Opus" }
      }
    }
  }
}
```

### 使用方式

#### 方式 1：作为主模型（推荐）

直接使用 CLI backend 作为主模型：
```json
{
  "agents": {
    "defaults": {
      "model": {
        "primary": "claude-cli/opus-4.5"
      }
    }
  }
}
```

**优势：**
- ✅ 使用 Cursor 账号，流量充足
- ✅ 避免 API 限流
- ✅ 代码处理成熟
- ⚠️ 注意：CLI backend 是文本模式，工具调用会被禁用

#### 方式 2：作为 Fallback（备用）

当 API 失败时自动切换到 CLI：
```json
{
  "agents": {
    "defaults": {
      "model": {
        "primary": "anthropic/claude-opus-4-5",
        "fallbacks": [
          "claude-cli/opus-4.5"
        ]
      }
    }
  }
}
```

**优势：**
- ✅ 平时使用 API（支持工具调用）
- ✅ API 失败时自动切换到 CLI
- ✅ 双重保障

## 方案二：通过 API 代理使用（如果 Cursor 提供 API）

### 如果 Cursor 有 API 端点

如果 Cursor 提供了 API 访问方式，可以配置为自定义 provider：

```json
{
  "models": {
    "providers": {
      "cursor": {
        "baseUrl": "https://api.cursor.sh/v1",  // 示例 URL
        "apiKey": "your-cursor-api-key",
        "api": "openai-completions",
        "models": [
          {
            "id": "claude-opus-4.5",
            "name": "Cursor Opus",
            "reasoning": true,
            "input": ["text"],
            "contextWindow": 200000,
            "maxTokens": 8192
          }
        ]
      }
    }
  },
  "agents": {
    "defaults": {
      "model": {
        "primary": "cursor/claude-opus-4.5"
      }
    }
  }
}
```

## 方案三：Google Antigravity 配置

### 如果 Antigravity 是 Google 的服务

如果 Google Antigravity 是 Google 的某个 AI 服务，可以配置：

```json
{
  "models": {
    "providers": {
      "antigravity": {
        "baseUrl": "https://antigravity.googleapis.com/v1",  // 示例
        "apiKey": "your-antigravity-api-key",
        "api": "openai-completions",
        "models": [
          {
            "id": "antigravity-pro",
            "name": "Antigravity Pro",
            "reasoning": true,
            "input": ["text", "image"],
            "contextWindow": 200000,
            "maxTokens": 8192
          }
        ]
      }
    }
  },
  "agents": {
    "defaults": {
      "model": {
        "primary": "antigravity/antigravity-pro"
      }
    }
  }
}
```

## 方案四：混合配置（最佳实践）

### 智能切换策略

```json
{
  "agents": {
    "defaults": {
      "cliBackends": {
        "claude-cli": {
          "command": "/opt/homebrew/bin/claude"
        }
      },
      "model": {
        "primary": "claude-cli/opus-4.5",
        "fallbacks": [
          "anthropic/claude-opus-4.5",
          "google/gemini-3-pro-preview"
        ]
      },
      "models": {
        "claude-cli/opus-4.5": { "alias": "Cursor" },
        "anthropic/claude-opus-4.5": { "alias": "API" },
        "google/gemini-3-pro-preview": { "alias": "Gemini" }
      },
      "thinkingDefault": "medium",
      "contextPruning": {
        "mode": "cache-ttl",
        "ttl": "24h",
        "keepLastAssistants": 5
      },
      "contextTokens": 150000
    }
  }
}
```

**工作流程：**
1. **优先使用** Cursor CLI（流量充足，避免限流）
2. **如果 CLI 失败**，切换到 API
3. **如果 API 也失败**，使用 Gemini 作为最后备用

## 配置示例（完整版）

### 推荐配置

```json
{
  "agents": {
    "defaults": {
      "cliBackends": {
        "claude-cli": {
          "command": "/opt/homebrew/bin/claude",
          "args": ["-p", "--output-format", "json", "--dangerously-skip-permissions"]
        }
      },
      "model": {
        "primary": "claude-cli/opus-4.5",
        "fallbacks": [
          "anthropic/claude-opus-4-5",
          "google/gemini-3-pro-preview"
        ]
      },
      "models": {
        "claude-cli/opus-4.5": { "alias": "Cursor Opus" },
        "claude-cli/sonnet-4.5": { "alias": "Cursor Sonnet" },
        "anthropic/claude-opus-4-5": { "alias": "API Opus" },
        "google/gemini-3-pro-preview": { "alias": "Gemini Pro" }
      },
      "thinkingDefault": "medium",
      "contextPruning": {
        "mode": "cache-ttl",
        "ttl": "24h",
        "keepLastAssistants": 5
      },
      "contextTokens": 150000,
      "timeoutSeconds": 600
    }
  }
}
```

## 验证配置

### 步骤 1：检查 CLI 是否可用

```bash
# 测试 Claude CLI
claude -p "Hello" --output-format json

# 如果成功，会返回 JSON 格式的响应
```

### 步骤 2：测试 OpenClaw 配置

```bash
cd /Users/oscar/moltbot/openclaw
source ~/.nvm/nvm.sh && nvm use 22

# 测试 CLI backend
pnpm openclaw agent --message "测试消息" --model claude-cli/opus-4.5
```

### 步骤 3：检查日志

```bash
tail -f ~/.openclaw/logs/gateway.log | grep -E "cli|backend|model"
```

## 注意事项

### CLI Backend 的限制

1. **工具调用被禁用**
   - CLI backend 是文本模式
   - 不支持工具调用（tool calls）
   - 只支持文本输入输出

2. **会话支持**
   - CLI backend 支持会话
   - 可以保持对话上下文
   - 但工具调用功能受限

3. **性能**
   - CLI 调用可能比 API 慢
   - 取决于本地 CLI 的性能

### 最佳实践

1. **混合使用**
   - 简单对话：使用 CLI backend（避免限流）
   - 复杂任务：使用 API（支持工具调用）

2. **Fallback 策略**
   - 主模型使用 CLI
   - API 作为 fallback（当需要工具调用时）

3. **监控使用**
   - 定期检查日志
   - 确认 CLI 正常工作
   - 监控 API 使用情况

## 故障排查

### 问题 1：找不到 CLI 命令

**解决方案：**
1. 确认 CLI 已安装
2. 使用绝对路径配置
3. 检查 PATH 环境变量

### 问题 2：CLI 调用失败

**解决方案：**
1. 检查 CLI 权限
2. 测试 CLI 命令是否正常工作
3. 查看错误日志

### 问题 3：会话不保持

**解决方案：**
1. 确认 CLI 支持会话
2. 检查 `sessionArg` 配置
3. 查看会话 ID 是否正确传递

## 下一步

1. **确认 Cursor CLI 路径**
   ```bash
   which claude
   # 或
   find / -name "claude" -type f 2>/dev/null | head -5
   ```

2. **配置 OpenClaw**
   - 编辑 `~/.openclaw/openclaw.json`
   - 添加 CLI backend 配置

3. **重启 Gateway**
   ```bash
   launchctl unload ~/Library/LaunchAgents/ai.openclaw.gateway.plist
   sleep 3
   launchctl load ~/Library/LaunchAgents/ai.openclaw.gateway.plist
   ```

4. **测试配置**
   - 发送测试消息
   - 检查是否使用 CLI backend
   - 验证响应质量

## 总结

通过配置 CLI backends，你可以：
- ✅ 利用 Cursor 账号的充足流量
- ✅ 避免 API 限流问题
- ✅ 使用成熟的代码处理能力
- ✅ 降低 API 成本

**推荐配置：**
- 主模型：`claude-cli/opus-4.5`（使用 Cursor）
- Fallback：`anthropic/claude-opus-4-5`（API，支持工具调用）
- 思考级别：`medium`
- 上下文修剪：启用

这样既能充分利用已有账号，又能保持功能完整性。
