#!/bin/bash

# 图片分析对比测试脚本
# 对比 Peekaboo 和 302 平台 GLM-4.6v-flash 的分析能力

set -euo pipefail

SCREENSHOT_PATH="${1:-/tmp/test_cursor_analysis.png}"
PLATFORM302_API_KEY="sk-eQ2fzH6DQyBKCwxcsr2cNRuop90nq7kAIfHuicRBIVfaMsRW"
PROMPT="请详细分析这个 Cursor IDE 聊天窗口。当前对话进行到哪里了？用户在问什么？AI 在回答什么？是否有错误或思路偏差？请用中文回答。"

echo "=========================================="
echo "图片分析对比测试"
echo "=========================================="
echo ""
echo "测试图片: $SCREENSHOT_PATH"
echo "提示词: $PROMPT"
echo ""

if [[ ! -f "$SCREENSHOT_PATH" ]]; then
    echo "❌ 错误：截图文件不存在: $SCREENSHOT_PATH"
    exit 1
fi

# 将图片转换为 base64
IMAGE_BASE64=$(base64 -i "$SCREENSHOT_PATH" 2>/dev/null || base64 "$SCREENSHOT_PATH")
IMAGE_SIZE=$(ls -lh "$SCREENSHOT_PATH" | awk '{print $5}')

echo "图片大小: $IMAGE_SIZE"
echo ""

# ==========================================
# 测试 1: Peekaboo (需要 OPENAI_API_KEY)
# ==========================================
echo "----------------------------------------"
echo "测试 1: Peekaboo (需要 OpenAI API Key)"
echo "----------------------------------------"

if [[ -z "${OPENAI_API_KEY:-}" ]]; then
    echo "⚠️  跳过：未设置 OPENAI_API_KEY"
    echo "   提示：Peekaboo 使用 OpenAI API，需要付费"
    PEEKABOO_RESULT="未测试（需要 OPENAI_API_KEY）"
    PEEKABOO_TIME="N/A"
else
    echo "开始测试..."
    START_TIME=$(date +%s.%N)
    PEEKABOO_OUTPUT=$(peekaboo see --path "$SCREENSHOT_PATH" --analyze "$PROMPT" 2>&1)
    END_TIME=$(date +%s.%N)
    PEEKABOO_TIME=$(echo "$END_TIME - $START_TIME" | bc)
    
    if echo "$PEEKABOO_OUTPUT" | grep -q "Error\|error\|失败"; then
        PEEKABOO_RESULT="❌ 失败: $PEEKABOO_OUTPUT"
    else
        PEEKABOO_RESULT="$PEEKABOO_OUTPUT"
    fi
fi

echo ""

# ==========================================
# 测试 2: 302 平台 GLM-4.6v-flash
# ==========================================
echo "----------------------------------------"
echo "测试 2: 302 平台 GLM-4.6v-flash (免费)"
echo "----------------------------------------"

echo "开始测试..."
START_TIME=$(date +%s.%N)

GLM_OUTPUT=$(curl -s -X POST "https://api.302.ai/v1/chat/completions" \
  -H "Authorization: Bearer $PLATFORM302_API_KEY" \
  -H "Content-Type: application/json" \
  -d "{
    \"model\": \"glm-4.6v-flash\",
    \"messages\": [
      {
        \"role\": \"user\",
        \"content\": [
          {
            \"type\": \"text\",
            \"text\": \"$PROMPT\"
          },
          {
            \"type\": \"image_url\",
            \"image_url\": {
              \"url\": \"data:image/png;base64,$IMAGE_BASE64\"
            }
          }
        ]
      }
    ],
    \"max_tokens\": 1000
  }" 2>&1)

END_TIME=$(date +%s.%N)
GLM_TIME=$(echo "$END_TIME - $START_TIME" | bc)

# 解析响应
if echo "$GLM_OUTPUT" | grep -q "error\|Error"; then
    GLM_RESULT="❌ 失败: $GLM_OUTPUT"
    GLM_TEXT=""
else
    GLM_TEXT=$(echo "$GLM_OUTPUT" | jq -r '.choices[0].message.content // "解析失败"' 2>/dev/null || echo "JSON 解析失败")
    if [[ -z "$GLM_TEXT" ]] || [[ "$GLM_TEXT" == "null" ]]; then
        GLM_RESULT="❌ 响应格式错误: $GLM_OUTPUT"
    else
        GLM_RESULT="✅ 成功"
    fi
fi

echo ""

# ==========================================
# 测试结果对比
# ==========================================
echo "=========================================="
echo "测试结果对比"
echo "=========================================="
echo ""

echo "【Peekaboo】"
echo "  响应时间: ${PEEKABOO_TIME:-N/A} 秒"
echo "  结果:"
echo "$PEEKABOO_RESULT" | sed 's/^/    /'
echo ""

echo "【302 平台 GLM-4.6v-flash】"
echo "  响应时间: ${GLM_TIME:-N/A} 秒"
echo "  结果:"
if [[ "$GLM_RESULT" == "✅ 成功" ]]; then
    echo "$GLM_TEXT" | sed 's/^/    /'
else
    echo "    $GLM_RESULT"
fi
echo ""

# ==========================================
# 总结
# ==========================================
echo "=========================================="
echo "总结"
echo "=========================================="
echo ""

if [[ -n "${PEEKABOO_TIME:-}" ]] && [[ "$PEEKABOO_TIME" != "N/A" ]]; then
    if (( $(echo "$GLM_TIME < $PEEKABOO_TIME" | bc -l) )); then
        echo "✅ GLM-4.6v-flash 更快 (${GLM_TIME}s vs ${PEEKABOO_TIME}s)"
    else
        echo "✅ Peekaboo 更快 (${PEEKABOO_TIME}s vs ${GLM_TIME}s)"
    fi
fi

echo ""
echo "成本对比:"
echo "  - Peekaboo: 需要 OpenAI API Key（付费）"
echo "  - GLM-4.6v-flash: 免费（可能有用量限制）"
echo ""

echo "建议:"
if [[ "$GLM_RESULT" == "✅ 成功" ]]; then
    echo "  ✅ GLM-4.6v-flash 可用，建议优先使用（免费）"
    if [[ -n "${OPENAI_API_KEY:-}" ]] && [[ "$PEEKABOO_RESULT" != "未测试"* ]]; then
        echo "  - 如果 GLM 分析不准确，可考虑 Peekaboo（付费但可能更准确）"
    fi
else
    echo "  ⚠️  GLM-4.6v-flash 测试失败，需要检查配置"
fi
