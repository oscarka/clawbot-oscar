# 快速配置：使用 Cursor 账号

## 发现

✅ 已检测到 Cursor 已安装：
- 应用位置：`/Applications/Cursor.app`
- CLI 位置：`/usr/local/bin/cursor`
- 配置目录：`~/.cursor`

## 方案选择

### 方案 A：如果 Cursor CLI 支持标准格式（推荐先试）

如果 Cursor CLI 支持类似 Claude CLI 的格式，可以直接配置：

```json
{
  "agents": {
    "defaults": {
      "cliBackends": {
        "cursor-cli": {
          "command": "/usr/local/bin/cursor",
          "args": ["--json"],
          "output": "json",
          "modelArg": "--model",
          "sessionArg": "--session",
          "sessionMode": "existing"
        }
      },
      "model": {
        "primary": "cursor-cli/default"
      }
    }
  }
}
```

### 方案 B：使用 Cursor 的 API（如果提供）

如果 Cursor 提供 API 访问，可以配置为自定义 provider。

### 方案 C：通过环境变量使用 Cursor 的认证

如果 Cursor 使用标准 Anthropic API，可以通过环境变量配置：

```bash
# 在 ~/.openclaw/.env 中添加
ANTHROPIC_API_KEY=your-cursor-api-key
```

然后 OpenClaw 会自动使用这个 API key。

## 立即测试步骤

### 步骤 1：测试 Cursor CLI

```bash
# 测试 Cursor CLI 是否支持标准格式
cursor --help

# 尝试发送消息（如果支持）
cursor "Hello" --json
```

### 步骤 2：检查 Cursor 配置

```bash
# 查看 Cursor 配置
cat ~/.cursor/config.json 2>/dev/null
ls -la ~/.cursor/
```

### 步骤 3：查找 API Key

如果 Cursor 使用 Anthropic API，可能在这里：
```bash
# 检查环境变量
env | grep -i anthropic

# 检查 Cursor 配置文件
find ~/.cursor -name "*.json" -exec grep -l "api.*key\|anthropic" {} \;
```

## 推荐配置（基于常见情况）

### 如果 Cursor 使用 Anthropic API

最简单的方式是通过环境变量：

1. **找到 Cursor 的 API Key**
   - 在 Cursor 设置中查找
   - 或在配置文件中查找

2. **配置到 OpenClaw**
   ```bash
   # 编辑 ~/.openclaw/.env
   echo "ANTHROPIC_API_KEY=your-cursor-api-key" >> ~/.openclaw/.env
   ```

3. **使用标准配置**
   ```json
   {
     "agents": {
       "defaults": {
         "model": {
           "primary": "anthropic/claude-opus-4-5"
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

这样 OpenClaw 就会使用 Cursor 账号的 API key，享受充足的流量。

## 下一步行动

1. **检查 Cursor CLI 格式**
   ```bash
   cursor --help
   ```

2. **查找 API Key**
   - 在 Cursor 应用中查看设置
   - 或检查配置文件

3. **配置 OpenClaw**
   - 根据找到的信息选择方案
   - 应用配置

4. **测试**
   - 重启 Gateway
   - 发送测试消息
   - 验证是否使用 Cursor 账号

## 需要的信息

请提供以下信息，我可以帮你精确配置：

1. **Cursor CLI 的帮助信息**
   ```bash
   cursor --help > cursor_help.txt
   ```

2. **Cursor 的 API Key**（如果找到）
   - 可以在 Cursor 设置中查找
   - 或告诉我如何找到

3. **Google Antigravity 的信息**
   - 这是什么服务？
   - 是否有 API 访问？
   - 是否有 CLI 工具？

有了这些信息，我可以给你最准确的配置方案。
