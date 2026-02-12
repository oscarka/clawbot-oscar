#!/bin/bash

# Cursor IDE 聊天窗口监控脚本
# 功能：监控 Cursor IDE 的聊天窗口，检测停止或偏差，通过 WhatsApp 通知用户
# 使用方法：bash cursor_monitor.sh [--interval 10] [--whatsapp +8613701223827]

set -euo pipefail

# 配置
INTERVAL=${CURSOR_MONITOR_INTERVAL:-10}  # 监控间隔（秒）
WHATSAPP_TARGET=${CURSOR_MONITOR_WHATSAPP:-"+8613701223827"}
CURSOR_APP="Cursor"
LOG_FILE="$HOME/.openclaw/cursor_monitor.log"
SCREENSHOT_DIR="$HOME/.openclaw/cursor_screenshots"
LAST_STATE_FILE="$HOME/.openclaw/cursor_last_state.txt"
GATEWAY_URL="http://127.0.0.1:18789"
GATEWAY_TOKEN="eee7905d1aeaf27ac8b0566184f6ab9d7c8ef7fd13c54b61"

# 解析参数
while [[ $# -gt 0 ]]; do
    case $1 in
        --interval)
            INTERVAL="$2"
            shift 2
            ;;
        --whatsapp)
            WHATSAPP_TARGET="$2"
            shift 2
            ;;
        *)
            echo "未知参数: $1"
            exit 1
            ;;
    esac
done

# 创建必要的目录
mkdir -p "$SCREENSHOT_DIR"
mkdir -p "$(dirname "$LOG_FILE")"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# 检查截图权限（实际测试）
check_permissions() {
    log "检查截图权限..."
    
    # 优先测试 Peekaboo
    local test_screenshot="/tmp/cursor_monitor_test_$$.png"
    local peekaboo_works=false
    local screencapture_works=false
    
    if peekaboo image --mode screen --path "$test_screenshot" 2>/dev/null && [ -f "$test_screenshot" ]; then
        rm -f "$test_screenshot"
        peekaboo_works=true
        log "✅ Peekaboo 可以截图（推荐，功能更强大）"
    else
        log "⚠️  Peekaboo 无法截图（权限可能未生效）"
    fi
    
    # 测试 screencapture 作为备选
    if screencapture -x "$test_screenshot" 2>/dev/null && [ -f "$test_screenshot" ]; then
        rm -f "$test_screenshot"
        screencapture_works=true
        log "✅ screencapture 可以截图（备选方案）"
    fi
    
    if [ "$peekaboo_works" = true ]; then
        USE_PEEKABOO=true
        return 0
    elif [ "$screencapture_works" = true ]; then
        USE_PEEKABOO=false
        log "⚠️  将使用 screencapture（功能受限，但可以工作）"
        log "   提示：如需 Peekaboo 的高级功能，请重启终端或重启电脑"
        return 0
    else
        log "❌ 所有截图方法都失败"
        log ""
        log "请确保："
        log "1. 系统设置 → 隐私与安全性 → 屏幕录制"
        log "2. Terminal（或你使用的终端）已勾选"
        log "3. 如果已勾选，尝试重启终端"
        exit 1
    fi
}

# 检查 Cursor 是否运行
check_cursor_running() {
    # 方法1: 使用 peekaboo 检查窗口（最可靠，因为需要窗口才能监控）
    local windows=$(peekaboo list windows --app "$CURSOR_APP" --json 2>/dev/null)
    if echo "$windows" | grep -q "\"name\".*\"Cursor\"" || echo "$windows" | grep -q "targetApplication"; then
        return 0
    fi
    
    # 方法2: 使用 osascript 检查进程（备选）
    if osascript -e 'tell application "System Events" to (name of processes) contains "Cursor"' 2>/dev/null | grep -qi "true"; then
        return 0
    fi
    
    # 方法3: 使用 ps 检查（最后备选）
    if ps aux | grep -i "[C]ursor.app" > /dev/null 2>&1; then
        return 0
    fi
    
    return 1
}

# 获取 Cursor 窗口信息
get_cursor_windows() {
    peekaboo list windows --app "$CURSOR_APP" --json 2>/dev/null || echo "[]"
}

# 截取 Cursor 聊天窗口（尝试找到聊天面板）
capture_chat_window() {
    local timestamp=$(date +%s)
    local screenshot_path="$SCREENSHOT_DIR/cursor_chat_${timestamp}.png"
    
    # 确保目录存在
    mkdir -p "$SCREENSHOT_DIR"
    
    # 根据权限检查结果选择方法
    if [ "${USE_PEEKABOO:-false}" = "true" ]; then
        # 使用 Peekaboo（更精确，可以定位到 Cursor 窗口）
        local peekaboo_output
        peekaboo_output=$(peekaboo image --app "$CURSOR_APP" --mode window --retina --path "$screenshot_path" 2>&1)
        local peekaboo_exit=$?
        
        if [ $peekaboo_exit -eq 0 ] && [ -f "$screenshot_path" ] && [ -s "$screenshot_path" ]; then
            echo "$screenshot_path"
            return 0
        else
            log "⚠️  Peekaboo 窗口截图失败 (exit: $peekaboo_exit): $peekaboo_output"
        fi
        
        # 如果窗口截图失败，尝试全屏
        peekaboo_output=$(peekaboo image --mode screen --retina --path "$screenshot_path" 2>&1)
        peekaboo_exit=$?
        if [ $peekaboo_exit -eq 0 ] && [ -f "$screenshot_path" ] && [ -s "$screenshot_path" ]; then
            log "✅ 使用全屏截图（窗口截图失败）"
            echo "$screenshot_path"
            return 0
        else
            log "⚠️  Peekaboo 全屏截图也失败 (exit: $peekaboo_exit): $peekaboo_output"
        fi
    fi
    
    # 使用 screencapture（备选方案，只能截全屏）
    if screencapture -x "$screenshot_path" 2>/dev/null && [ -f "$screenshot_path" ] && [ -s "$screenshot_path" ]; then
        log "✅ 使用 screencapture 截图"
        echo "$screenshot_path"
        return 0
    fi
    
    log "❌ 所有截图方法都失败"
    return 1
}

# 分析截图内容（使用 302 平台的 GLM-4.6v-flash 模型）
analyze_screenshot() {
    local screenshot_path="$1"
    local prompt="$2"
    local platform302_api_key="sk-eQ2fzH6DQyBKCwxcsr2cNRuop90nq7kAIfHuicRBIVfaMsRW"
    
    # 将图片转换为 base64
    local image_base64
    if command -v base64 >/dev/null 2>&1; then
        image_base64=$(base64 -i "$screenshot_path" 2>/dev/null || base64 "$screenshot_path")
    else
        log "❌ 错误：未找到 base64 命令"
        echo "分析失败：缺少 base64 工具"
        return 1
    fi
    
    # 调用 302 平台的 GLM-4.6v-flash API
    local response=$(curl -s -X POST "https://api.302.ai/v1/chat/completions" \
      -H "Authorization: Bearer $platform302_api_key" \
      -H "Content-Type: application/json" \
      -d "{
        \"model\": \"glm-4.6v-flash\",
        \"messages\": [
          {
            \"role\": \"user\",
            \"content\": [
              {
                \"type\": \"text\",
                \"text\": \"$prompt\"
              },
              {
                \"type\": \"image_url\",
                \"image_url\": {
                  \"url\": \"data:image/png;base64,$image_base64\"
                }
              }
            ]
          }
        ],
        \"max_tokens\": 1000
      }" 2>&1)
    
    # 解析响应
    if echo "$response" | grep -q "error\|Error"; then
        log "⚠️  API 调用失败: $response"
        echo "分析失败：API 错误"
        return 1
    fi
    
    local analysis=$(echo "$response" | jq -r '.choices[0].message.content // "解析失败"' 2>/dev/null)
    if [[ -z "$analysis" ]] || [[ "$analysis" == "null" ]]; then
        log "⚠️  响应解析失败: $response"
        echo "分析失败：响应格式错误"
        return 1
    fi
    
    echo "$analysis"
}

# 检测窗口是否停止更新
# 方法：通过比较图片哈希值判断内容是否变化
detect_stopped_window() {
    local current_screenshot="$1"
    local last_state_file="$LAST_STATE_FILE"
    
    # 计算当前截图的哈希值（MD5）
    local current_hash
    if command -v md5 >/dev/null 2>&1; then
        current_hash=$(md5 -q "$current_screenshot" 2>/dev/null)
    elif command -v md5sum >/dev/null 2>&1; then
        current_hash=$(md5sum "$current_screenshot" 2>/dev/null | cut -d' ' -f1)
    else
        # 如果没有 md5，使用文件大小作为简单判断
        current_hash=$(stat -f %z "$current_screenshot" 2>/dev/null || echo "0")
    fi
    
    if [[ -z "$current_hash" ]]; then
        log "⚠️  无法计算截图哈希，跳过检测"
        return 1  # 未停止（保守策略）
    fi
    
    if [[ ! -f "$last_state_file" ]]; then
        # 第一次运行，保存哈希值
        echo "$current_hash" > "$last_state_file"
        return 1  # 未停止
    fi
    
    local last_hash=$(cat "$last_state_file" 2>/dev/null)
    
    # 如果哈希值相同，说明内容没有变化
    if [[ "$current_hash" == "$last_hash" ]]; then
        # 检查距离上次变化的时间
        local last_change_file="${last_state_file}.timestamp"
        local last_change_time
        if [[ -f "$last_change_file" ]]; then
            last_change_time=$(cat "$last_change_file" 2>/dev/null || echo "0")
        else
            last_change_time=$(date +%s)
            echo "$last_change_time" > "$last_change_file"
        fi
        
        local current_time=$(date +%s)
        local time_since_change=$((current_time - last_change_time))
        
        # 如果超过 30 秒没有变化，认为停止
        if [[ $time_since_change -gt 30 ]]; then
            log "⏸️  检测到窗口内容未变化超过 ${time_since_change} 秒"
            return 0  # 已停止
        fi
    else
        # 内容有变化，更新状态和时间戳
        echo "$current_hash" > "$last_state_file"
        echo "$(date +%s)" > "${last_state_file}.timestamp"
    fi
    
    return 1  # 未停止
}

# 通过 OpenClaw Gateway 发送 WhatsApp 消息
send_whatsapp_notification() {
    local message="$1"
    local screenshot_path="${2:-}"
    
    log "📱 发送 WhatsApp 通知..."
    
    # 通过 Gateway RPC 发送消息
    local response=$(curl -s -X POST "$GATEWAY_URL/rpc" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer $GATEWAY_TOKEN" \
        -d "{
            \"method\": \"send\",
            \"params\": {
                \"channel\": \"whatsapp\",
                \"to\": \"$WHATSAPP_TARGET\",
                \"message\": \"$message\"
            }
        }" 2>&1) || {
        log "⚠️ 发送失败，尝试使用 CLI..."
        # 备用方案：使用 CLI
        cd /Users/oscar/moltbot/openclaw && \
        pnpm openclaw gateway call send \
            --params "{\"channel\":\"whatsapp\",\"to\":\"$WHATSAPP_TARGET\",\"message\":\"$message\"}" \
            2>&1 | tee -a "$LOG_FILE" || true
    }
    
    log "✅ 通知已发送"
}

# 主监控循环
main_loop() {
    log "🚀 开始监控 Cursor IDE 聊天窗口..."
    log "监控间隔: ${INTERVAL}秒"
    log "WhatsApp 目标: $WHATSAPP_TARGET"
    
    local consecutive_stops=0
    local last_notification_time=0
    local notification_cooldown=300  # 5分钟内不重复通知
    
    while true; do
        # 检查 Cursor 是否运行
        if ! check_cursor_running; then
            log "⏸️  Cursor 未运行，等待..."
            sleep $INTERVAL
            continue
        fi
        
        # 截取窗口
        local screenshot=$(capture_chat_window)
        if [[ ! -f "$screenshot" ]]; then
            log "⚠️  截图失败，跳过本次检查"
            sleep $INTERVAL
            continue
        fi
        
        # 检测是否停止
        if detect_stopped_window "$screenshot"; then
            consecutive_stops=$((consecutive_stops + 1))
            log "⏸️  检测到窗口停止更新 (连续: $consecutive_stops 次)"
            
            # 如果连续停止超过 3 次，且距离上次通知超过冷却时间
            local current_time=$(date +%s)
            if [[ $consecutive_stops -ge 3 ]] && [[ $((current_time - last_notification_time)) -gt $notification_cooldown ]]; then
                log "🔔 触发通知..."
                
                # 分析截图
                local analysis=$(analyze_screenshot "$screenshot" \
                    "分析这个 Cursor IDE 聊天窗口。当前对话进行到哪里了？是否有错误或思路偏差？")
                
                # 构建通知消息
                local message="🤖 Cursor 监控通知

检测到 Cursor IDE 聊天窗口已停止更新超过 $((consecutive_stops * INTERVAL)) 秒。

分析结果：
$analysis

请选择操作：
1. 暂停 - 停止当前任务
2. 修改 - 我来调整对话方向
3. 继续 - 忽略此通知

截图已保存: $screenshot"
                
                # 发送通知
                send_whatsapp_notification "$message" "$screenshot"
                last_notification_time=$current_time
                consecutive_stops=0  # 重置计数器
            fi
        else
            consecutive_stops=0
            log "✅ 窗口正常更新"
        fi
        
        sleep $INTERVAL
    done
}

# 主函数
main() {
    log "=========================================="
    log "Cursor IDE 监控脚本启动"
    log "=========================================="
    
    check_permissions
    
    # 捕获退出信号
    trap 'log "脚本已停止"; exit 0' INT TERM
    
    main_loop
}

# 运行
main "$@"
