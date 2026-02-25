# 飞书发小红书 - 快速测试指南

## 已完成的配置

以下已就绪，无需你再改：

- **mcporter 配置**：`~/.mcporter/mcporter.json` 和 `moltbot/config/mcporter.json` 已添加 xhs-toolkit
- **Agent 能力**：系统提示已加入小红书发布说明，Agent 会使用 `mcporter call xhs-toolkit.smart_publish_note` 发布
- **安装脚本**：`scripts/setup_xhs_mcp.sh` 可一键完成环境安装

---

## 你需要做的（按顺序）

### 1. 克隆 xhs-toolkit

```bash
cd /Users/oscar/moltbot
git clone https://github.com/aki66938/xhs-toolkit.git
```

若网络不佳，可在浏览器打开 https://github.com/aki66938/xhs-toolkit 下载 ZIP 并解压到 `moltbot/xhs-toolkit`。

### 2. 安装 xhs-toolkit 依赖

```bash
cd /Users/oscar/moltbot/xhs-toolkit
# 使用 Python 3.12 创建虚拟环境并安装（系统需有 Python 3.10+）：
/usr/local/bin/python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. 配置 xhs-toolkit

```bash
cp env_example .env
# 编辑 .env，至少填写：
# CHROME_PATH="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
# WEBDRIVER_CHROME_DRIVER 的路径（如 brew install chromedriver 后的 /opt/homebrew/bin/chromedriver）
```

### 4. 首次登录小红书

```bash
cd /Users/oscar/moltbot/xhs-toolkit
./xhs cookie save
# 或: uv run python xhs_toolkit.py cookie save
```

浏览器会打开，登录小红书创作者中心，完成后在终端按回车保存 Cookie。

### 5. 安装 mcporter

```bash
npm install -g mcporter
```

### 6. 确认 OpenClaw gateway 运行

若已用飞书对接 OpenClaw，确保 gateway 在跑。如有变更，可重启：

```bash
openclaw gateway restart
```

---

## 飞书测试

在飞书里给机器人发消息，例如：

1. **纯文字**：
   > 帮我把这段话发到小红书：标题「今日分享」，内容「测试飞书发小红书」

2. **带话题**：
   > 发布到小红书，标题「周末探店」，内容「发现一家很棒的咖啡馆」，话题加上「探店」「咖啡」

3. **带图片**（需要本地路径）：
   > 发一篇小红书，标题「今日美食」，内容「今天的午餐」，图片在 /Users/oscar/xxx.jpg

首次测试建议先用纯文字，确认能发成功后，再试图片和话题。

---

## 若 mcporter 使用 uv 失败

若系统没有 uv，可把 `~/.mcporter/mcporter.json` 里的 xhs-toolkit 配置改成：

```json
"xhs-toolkit": {
  "command": "python3",
  "args": ["-m", "src.server.mcp_server", "--stdio"],
  "cwd": "/Users/oscar/moltbot/xhs-toolkit",
  "env": { "PYTHONPATH": "/Users/oscar/moltbot/xhs-toolkit" }
}
```

---

## 故障排查

- **mcporter 找不到**：执行 `npm install -g mcporter`，或检查 PATH
- **xhs-toolkit 连接失败**：确认 xhs-toolkit 已克隆、依赖已装、`.env` 已配置
- **ChromeDriver 版本不符**：Chrome 和 ChromeDriver 版本需一致，可在 https://googlechromelabs.github.io/chrome-for-testing/ 下载对应版本
