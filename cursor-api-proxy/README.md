# Cursor API Proxy

将 Cursor 的能力封装为 OpenAI 兼容的 API，供 OpenClaw 使用。

## 功能

- 提供 OpenAI 兼容的 `/v1/chat/completions` 端点
- 接收 OpenClaw 的请求
- 调用 Cursor 使用的 API（Anthropic Claude API）
- 返回标准响应格式

## 安装

```bash
pip install -r requirements.txt
```

## 配置

1. 复制 `.env.example` 为 `.env`
2. 填入你的 Anthropic API Key（从 Cursor 设置中获取）

## 运行

```bash
python main.py
```

或使用 uvicorn：

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

## 配置 OpenClaw

在 `~/.openclaw/openclaw.json` 中添加：

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
