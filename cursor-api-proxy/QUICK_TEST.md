# 快速测试指南

## 启动服务

直接运行：

```bash
cd /Users/oscar/moltbot/cursor-api-proxy
python3 main.py
```

服务将在 `http://localhost:8000` 启动。

## 测试步骤

### 1. 健康检查

打开新终端，运行：

```bash
curl http://localhost:8000/
```

应该返回：
```json
{"status":"ok","service":"Cursor API Proxy","version":"1.0.0"}
```

### 2. 列出模型

```bash
curl http://localhost:8000/v1/models
```

应该返回模型列表。

### 3. 测试聊天（简单）

```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer cursor-proxy-key" \
  -d '{
    "model": "claude-opus-4-5",
    "messages": [
      {"role": "user", "content": "Say hi in one sentence"}
    ],
    "max_tokens": 50
  }'
```

### 4. 测试聊天（格式化输出）

```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer cursor-proxy-key" \
  -d '{
    "model": "claude-opus-4-5",
    "messages": [
      {"role": "user", "content": "Say hi in one sentence"}
    ],
    "max_tokens": 50
  }' | python3 -m json.tool
```

## 如果遇到错误

### 错误：ModuleNotFoundError

需要安装依赖：
```bash
pip3 install fastapi uvicorn anthropic python-dotenv pydantic
```

### 错误：ANTHROPIC_API_KEY not found

检查 `.env` 文件是否存在，并且包含：
```
ANTHROPIC_API_KEY=sk-ant-api03-...
```

### 错误：端口被占用

检查端口是否被占用：
```bash
lsof -i :8000
```

如果被占用，可以修改 `main.py` 中的端口号，或修改 `.env` 中的 `PROXY_PORT`。

## 停止服务

在运行服务的终端按 `Ctrl+C` 停止。
