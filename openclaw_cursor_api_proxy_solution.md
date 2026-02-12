# 将 Cursor 功能封装为 API 供 OpenClaw 使用的具体方案

## 核心思路

创建一个 API 代理服务，将 Cursor 的能力暴露为标准的 OpenAI 兼容 API，然后让 OpenClaw 通过自定义 provider 配置使用这个 API。

## 方案架构

```
OpenClaw Gateway
    ↓ (HTTP Request)
API 代理服务 (FastAPI/Express)
    ↓ (调用 Cursor 的能力)
Cursor 账号的 API (Anthropic/OpenAI)
    ↓ (返回结果)
API 代理服务
    ↓ (标准 API 响应)
OpenClaw Gateway
```

## 实施步骤

### 步骤 1：创建 API 代理服务

创建一个简单的 HTTP 服务，提供 OpenAI 兼容的 API 端点。

#### 服务功能

1. **接收 OpenClaw 的请求**
   - 提供 `/v1/chat/completions` 端点
   - 接收标准的 OpenAI 格式请求

2. **调用 Cursor 使用的 API**
   - 如果 Cursor 使用 Anthropic API，直接调用
   - 如果 Cursor 使用其他 API，相应调用

3. **返回标准响应**
   - 返回 OpenAI 兼容的响应格式
   - 支持流式响应（如果需要）

#### 技术选择

- **Python + FastAPI**（推荐，简单快速）
- **Node.js + Express**（如果熟悉 JavaScript）
- **Go + Gin**（如果需要高性能）

### 步骤 2：获取 Cursor 使用的 API 凭证

#### 方法 A：从 Cursor 配置中提取

1. 打开 Cursor
2. 查看设置中的 API 配置
3. 找到使用的 API provider（可能是 Anthropic、OpenAI 等）
4. 提取 API Key 或 Token

#### 方法 B：通过 Cursor 的 CLI 或扩展

如果 Cursor 提供 CLI 或扩展接口，可以通过这些接口调用。

### 步骤 3：实现代理服务

#### Python + FastAPI 示例结构

创建一个简单的代理服务：

**文件结构：**
```
cursor-api-proxy/
├── main.py          # FastAPI 主服务
├── requirements.txt  # 依赖
├── .env            # 环境变量（API Key）
└── README.md       # 说明文档
```

**核心功能：**
1. 接收 `/v1/chat/completions` 请求
2. 提取请求参数（messages, model, temperature 等）
3. 调用 Cursor 使用的 API（如 Anthropic API）
4. 转换响应格式为 OpenAI 兼容格式
5. 返回给 OpenClaw

### 步骤 4：配置 OpenClaw 使用代理

在 `~/.openclaw/openclaw.json` 中添加自定义 provider：

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

### 步骤 5：启动和使用

1. **启动代理服务**
   ```bash
   cd cursor-api-proxy
   python main.py
   # 或
   uvicorn main:app --host 0.0.0.0 --port 8000
   ```

2. **重启 OpenClaw Gateway**
   ```bash
   launchctl unload ~/Library/LaunchAgents/ai.openclaw.gateway.plist
   sleep 3
   launchctl load ~/Library/LaunchAgents/ai.openclaw.gateway.plist
   ```

3. **测试**
   - 通过 OpenClaw 发送消息
   - 检查是否使用 Cursor 代理
   - 验证响应质量

## 具体实现细节

### API 代理服务需要实现的功能

1. **请求转换**
   - 接收 OpenAI 格式的请求
   - 转换为 Cursor 使用的 API 格式（如 Anthropic 格式）

2. **API 调用**
   - 使用 Cursor 的 API Key
   - 调用相应的 API endpoint
   - 处理错误和重试

3. **响应转换**
   - 将 API 响应转换为 OpenAI 格式
   - 保持流式响应（如果支持）

4. **认证和授权**
   - 验证 OpenClaw 的请求
   - 使用 Cursor 的 API Key

### 需要考虑的问题

1. **API 格式差异**
   - OpenAI 和 Anthropic 的 API 格式不同
   - 需要正确转换消息格式
   - 需要处理参数映射

2. **流式响应**
   - 如果 Cursor 使用的 API 支持流式响应
   - 需要正确转发流式数据

3. **错误处理**
   - API 限流
   - 网络错误
   - 认证错误

4. **性能优化**
   - 连接池
   - 请求缓存（如果需要）
   - 超时处理

## 关于 Google Antigravity

Antigravity 作为 Google 的 IDE 工具，可能使用 Google 的 API（如 Gemini API）。可以创建类似的代理服务：

1. **创建 Antigravity 代理服务**
   - 调用 Google Gemini API
   - 转换为 OpenAI 兼容格式

2. **配置 OpenClaw**
   - 添加 `antigravity-proxy` provider
   - 配置使用 Antigravity 的模型

## 优势

1. **不改动 OpenClaw 代码**
   - 只添加配置
   - 使用标准的 provider 机制

2. **充分利用 Cursor 账号**
   - 使用已购买的流量
   - 利用成熟的代码处理能力

3. **灵活扩展**
   - 可以添加缓存
   - 可以添加日志
   - 可以添加监控

4. **易于维护**
   - 代理服务独立运行
   - 可以单独更新和优化

## 实施建议

### 快速原型（MVP）

1. **创建最简单的代理服务**
   - 只实现基本的请求/响应转换
   - 先不考虑流式响应
   - 先不考虑复杂错误处理

2. **测试基本功能**
   - 确保可以接收请求
   - 确保可以调用 API
   - 确保可以返回响应

3. **逐步完善**
   - 添加流式响应支持
   - 添加错误处理
   - 添加监控和日志

### 生产环境考虑

1. **服务部署**
   - 使用 systemd 或 launchd 管理服务
   - 确保服务自动重启
   - 添加健康检查

2. **安全性**
   - API Key 加密存储
   - 请求认证
   - 日志脱敏

3. **性能**
   - 连接池
   - 请求限流
   - 缓存策略

## 下一步行动

1. **确认 Cursor 使用的 API**
   - 查看 Cursor 设置
   - 确认 API provider 和 Key

2. **创建代理服务**
   - 选择技术栈
   - 实现基本功能

3. **配置 OpenClaw**
   - 添加 provider 配置
   - 测试连接

4. **优化和完善**
   - 添加必要功能
   - 优化性能

需要我帮你创建代理服务的代码框架吗？
