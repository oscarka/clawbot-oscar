# Cursor API Proxy 设置指南

## ✅ 方案验证结果

**方案可行！** 代理服务已成功创建并测试。

## 项目结构

```
cursor-api-proxy/
├── main.py              # 主服务文件
├── requirements.txt     # Python 依赖
├── .env.example        # 环境变量示例
├── .gitignore          # Git 忽略文件
├── README.md           # 项目说明
├── TEST_RESULTS.md     # 测试结果
└── SETUP_GUIDE.md      # 本文件
```

## 快速开始

### 1. 安装依赖

```bash
cd cursor-api-proxy
python3 -m pip install --user fastapi uvicorn anthropic python-dotenv pydantic
```

### 2. 配置环境变量

复制 `.env.example` 为 `.env` 并填入你的 Anthropic API Key：

```bash
cp .env.example .env
# 编辑 .env 文件，填入 ANTHROPIC_API_KEY
```

### 3. 启动服务

```bash
python3 main.py
```

服务将在 `http://localhost:8000` 启动。

### 4. 测试服务

```bash
# 健康检查
curl http://localhost:8000/

# 列出模型
curl http://localhost:8000/v1/models

# 测试聊天
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer cursor-proxy-key" \
  -d '{
    "model": "claude-opus-4-5",
    "messages": [{"role": "user", "content": "Hello"}],
    "max_tokens": 100
  }'
```

## 配置 OpenClaw

### 步骤 1：编辑 OpenClaw 配置

编辑 `~/.openclaw/openclaw.json`，添加以下配置：

```json
{
  "models": {
    "providers": {
      "cursor-proxy": {
        "baseUrl": "http://localhost:8000/v1",
        "apiKey": "cursor-proxy-key",
        "api": "openai-completions",
        "models": [
          {
            "id": "claude-opus-4-5",
            "name": "Cursor Opus",
            "reasoning": true,
            "input": ["text"],
            "contextWindow": 200000,
            "maxTokens": 8192
          },
          {
            "id": "claude-sonnet-4-5",
            "name": "Cursor Sonnet",
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
        "primary": "cursor-proxy/claude-opus-4-5"
      }
    }
  }
}
```

### 步骤 2：重启 OpenClaw Gateway

```bash
launchctl unload ~/Library/LaunchAgents/ai.openclaw.gateway.plist
sleep 3
launchctl load ~/Library/LaunchAgents/ai.openclaw.gateway.plist
```

### 步骤 3：测试

通过 OpenClaw 发送消息，验证是否使用代理服务。

## 作为系统服务运行（可选）

### macOS (launchd)

创建 `~/Library/LaunchAgents/com.cursor.proxy.plist`：

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.cursor.proxy</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/local/bin/python3</string>
        <string>/Users/oscar/moltbot/cursor-api-proxy/main.py</string>
    </array>
    <key>WorkingDirectory</key>
    <string>/Users/oscar/moltbot/cursor-api-proxy</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/tmp/cursor-proxy.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/cursor-proxy.err.log</string>
</dict>
</plist>
```

加载服务：

```bash
launchctl load ~/Library/LaunchAgents/com.cursor.proxy.plist
```

## 功能说明

### 支持的端点

1. **GET /** - 健康检查
2. **GET /v1/models** - 列出可用模型
3. **POST /v1/chat/completions** - 聊天完成（支持流式和非流式）

### 支持的模型

- `claude-opus-4-5` - Claude Opus 4.5
- `claude-sonnet-4-5` - Claude Sonnet 4.5
- `claude-haiku-3-5` - Claude Haiku 3.5

### 请求格式

使用标准的 OpenAI API 格式：

```json
{
  "model": "claude-opus-4-5",
  "messages": [
    {"role": "user", "content": "Hello"}
  ],
  "temperature": 0.7,
  "max_tokens": 4096,
  "stream": false
}
```

## 注意事项

1. **API Key 安全**
   - 确保 `.env` 文件不被提交到版本控制
   - 使用强密码作为 `PROXY_API_KEY`

2. **服务可用性**
   - 代理服务需要持续运行
   - 建议使用系统服务管理（launchd/systemd）

3. **性能考虑**
   - 代理服务会增加少量延迟
   - 对于生产环境，考虑添加缓存和连接池

4. **错误处理**
   - 当前版本包含基本错误处理
   - 可以根据需要添加更详细的日志和监控

## 故障排查

### 服务无法启动

1. 检查 Python 版本：`python3 --version`
2. 检查依赖安装：`python3 -c "import fastapi"`
3. 检查端口占用：`lsof -i :8000`

### OpenClaw 无法连接

1. 确认代理服务正在运行：`curl http://localhost:8000/`
2. 检查 OpenClaw 配置中的 `baseUrl` 是否正确
3. 检查防火墙设置

### API 调用失败

1. 检查 `.env` 文件中的 `ANTHROPIC_API_KEY` 是否正确
2. 检查 API Key 是否有足够的配额
3. 查看代理服务日志：`cat /tmp/cursor-proxy.log`

## 下一步优化

1. **添加认证**
   - 实现更严格的 API Key 验证
   - 添加请求限流

2. **性能优化**
   - 添加连接池
   - 实现响应缓存

3. **监控和日志**
   - 添加详细的请求日志
   - 实现健康检查端点

4. **功能扩展**
   - 支持更多模型
   - 添加流式响应优化
