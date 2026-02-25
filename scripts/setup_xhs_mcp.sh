#!/bin/bash
# 小红书 xhs-toolkit MCP 快速安装脚本
# 用法: ./scripts/setup_xhs_mcp.sh

set -e
cd "$(dirname "$0")/.."
MOLTBOT_ROOT="$(pwd)"
XHS_DIR="$MOLTBOT_ROOT/xhs-toolkit"

echo "📕 小红书 MCP 安装脚本"
echo "======================="

# 1. 克隆 xhs-toolkit
if [ ! -d "$XHS_DIR" ]; then
  echo "1. 克隆 xhs-toolkit..."
  git clone --depth 1 https://github.com/aki66938/xhs-toolkit.git "$XHS_DIR"
else
  echo "1. xhs-toolkit 已存在，跳过克隆"
fi

# 2. 安装 xhs-toolkit 依赖
echo "2. 安装 xhs-toolkit 依赖..."
cd "$XHS_DIR"
if command -v uv &>/dev/null; then
  uv sync
else
  pip install -r requirements.txt
fi

# 3. 配置 .env
if [ ! -f "$XHS_DIR/.env" ]; then
  echo "3. 创建 .env 配置..."
  cp "$XHS_DIR/env_example" "$XHS_DIR/.env"
  echo "   请编辑 $XHS_DIR/.env，填写 CHROME_PATH 和 WEBDRIVER_CHROME_DRIVER"
  echo "   macOS 示例: CHROME_PATH=\"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome\""
  echo "   ChromeDriver: brew install --cask chromedriver 或从 https://googlechromelabs.github.io/chrome-for-testing/ 下载"
else
  echo "3. .env 已存在，跳过"
fi

# 4. 安装 mcporter
echo "4. 安装 mcporter..."
npm install -g mcporter

echo ""
echo "✅ 安装完成！接下来请手动执行："
echo "   1. 编辑 $XHS_DIR/.env 配置 Chrome 路径"
echo "   2. 首次登录: cd $XHS_DIR && ./xhs cookie save  （或 uv run python xhs_toolkit.py cookie save）"
echo "   3. 在飞书中发消息测试: \"帮我把这句话发到小红书：标题今日分享，内容测试一下\""
echo ""
