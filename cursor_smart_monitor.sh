#!/bin/bash

# Cursor IDE 智能监控脚本
# 功能：
# 1. 理解用户在做什么（查看聊天记录、等待响应等）
# 2. 分析 Cursor 输出的内容
# 3. 智能判断是否真的卡住（而不只是内容没变化）
# 4. 通过 WhatsApp 发送详细分析报告

set -euo pipefail

# 配置
INTERVAL=${CURSOR_SMART_MONITOR_INTERVAL:-15}  # 监控间隔（秒）
WHATSAPP_TARGET=${CURSOR_SMART_MONITOR_WHATSAPP:-"+8613701223827"}
CURSOR_APP="Cursor"
LOG_FILE="$HOME/.openclaw/cursor_smart_monitor.log"
SCREENSHOT_DIR="$HOME/.openclaw/cursor_screenshots"
STATE_DIR="$HOME/.openclaw/cursor_monitor_state"
PLATFORM302_API_KEY="sk-eQ2fzH6DQyBKCwxcsr2cNRuop90nq7kAIfHuicRBIVfaMsRW"
GATEWAY_URL="http://127.0.0.1:18789"
GATEWAY_TOKEN="eee7905d1aeaf27ac8b0566184f6ab9d7c8ef7fd13c54b61"

# 创建必要的目录
mkdir -p "$SCREENSHOT_DIR"
mkdir -p "$STATE_DIR"
mkdir -p "$(dirname "$LOG_FILE")"

log() {
    local level="${2:-INFO}"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[$timestamp] [$level] $1" | tee -a "$LOG_FILE" >&2
}

log_debug() {
    log "$1" "DEBUG"
}

log_info() {
    log "$1" "INFO"
}

log_warn() {
    log "$1" "WARN"
}

log_error() {
    log "$1" "ERROR"
}

# 检查 Cursor 是否运行
check_cursor_running() {
    local windows=$(peekaboo list windows --app "$CURSOR_APP" --json 2>/dev/null)
    if echo "$windows" | grep -q "\"name\".*\"Cursor\"" || echo "$windows" | grep -q "targetApplication"; then
        return 0
    fi
    if osascript -e 'tell application "System Events" to (name of processes) contains "Cursor"' 2>/dev/null | grep -qi "true"; then
        return 0
    fi
    if ps aux | grep -i "[C]ursor.app" > /dev/null 2>&1; then
        return 0
    fi
    return 1
}

# 截取 Cursor 窗口
capture_cursor_window() {
    local timestamp=$(date +%s)
    local screenshot_path="$SCREENSHOT_DIR/cursor_${timestamp}.png"
    mkdir -p "$SCREENSHOT_DIR"
    
    log_debug "开始截图: $screenshot_path"
    
    # 优先使用 Peekaboo
    log_debug "尝试使用 Peekaboo 截图..."
    local peekaboo_output
    peekaboo_output=$(peekaboo image --app "$CURSOR_APP" --mode window --retina --path "$screenshot_path" 2>&1)
    local peekaboo_exit=$?
    log_debug "Peekaboo 退出码: $peekaboo_exit, 输出: $peekaboo_output"
    
    if [ $peekaboo_exit -eq 0 ] && [ -f "$screenshot_path" ] && [ -s "$screenshot_path" ]; then
        local file_size=$(ls -lh "$screenshot_path" | awk '{print $5}')
        log_info "✅ Peekaboo 截图成功: $screenshot_path (大小: $file_size)" >&2
        echo "$screenshot_path" >&1
        return 0
    fi
    
    # 备选：使用 screencapture
    log_debug "Peekaboo 失败，尝试使用 screencapture..." >&2
    if screencapture -x "$screenshot_path" 2>/dev/null && [ -f "$screenshot_path" ] && [ -s "$screenshot_path" ]; then
        local file_size=$(ls -lh "$screenshot_path" | awk '{print $5}')
        log_info "✅ screencapture 截图成功: $screenshot_path (大小: $file_size)" >&2
        echo "$screenshot_path" >&1
        return 0
    fi
    
    # 如果都失败，记录错误
    log_error "截图失败 - Peekaboo exit: $peekaboo_exit, output: $peekaboo_output"
    if [ -f "$screenshot_path" ]; then
        log_debug "文件存在但可能为空，大小: $(ls -lh "$screenshot_path" | awk '{print $5}')"
    else
        log_debug "文件不存在"
    fi
    return 1
}

# 智能分析截图内容（使用 GLM-4.6v-flash）
analyze_screenshot_intelligently() {
    local screenshot_path="$1"
    local previous_analysis="${2:-}"
    
    # 构建智能分析提示词
    local prompt="你是一个专业的 AI 助手监控系统。请详细分析这个 Cursor IDE 聊天窗口的截图。

**分析要求：**

1. **当前状态判断：**
   - 用户在做什么？（查看历史记录、等待 AI 响应、输入问题、查看代码等）
   - Cursor AI 在做什么？（正在思考、正在生成代码、已完成响应、等待用户输入等）
   - 对话进行到哪个阶段？（初始阶段、进行中、已完成、卡住等）

2. **内容分析：**
   - 用户最近的问题是什么？
   - AI 的回复内容是什么？（如果可见）
   - 是否有错误信息或警告？
   - 代码生成是否完成？

3. **问题检测：**
   - 是否真的卡住了？（区分：正在思考 vs 真的卡住）
   - 是否有思路偏差？（AI 理解错误、方向不对等）
   - 是否需要人工干预？

4. **上下文理解：**
   - 如果用户在往上翻聊天记录，说明什么？
   - 如果 AI 长时间没有新输出，可能的原因是什么？
   - 当前任务是否正常进行？

**请用中文回答，格式清晰，重点突出。**"

    # 如果有之前的分析，加入上下文
    if [[ -n "$previous_analysis" ]]; then
        prompt="$prompt

**之前的分析：**
$previous_analysis

**请对比当前状态和之前的状态，判断是否有变化或进展。**"
    fi
    
    # 调用 GLM-4.6v-flash API
    log_debug "开始转换图片为 base64..."
    local image_base64
    if command -v base64 >/dev/null 2>&1; then
        image_base64=$(base64 -i "$screenshot_path" 2>/dev/null || base64 "$screenshot_path")
        local base64_size=${#image_base64}
        log_debug "Base64 转换完成，大小: $base64_size 字符"
    else
        log_error "未找到 base64 命令"
        return 1
    fi
    
    # 构建 JSON 请求体（使用临时文件避免 shell 转义问题）
    local temp_json=$(mktemp /tmp/cursor_api_XXXXXX.json 2>/dev/null || echo "/tmp/cursor_api_$$_$(date +%s).json")
    log_debug "创建临时 JSON 文件: $temp_json"
    cat > "$temp_json" <<EOF
{
  "model": "glm-4.6v-flash",
  "messages": [
    {
      "role": "user",
      "content": [
        {
          "type": "text",
          "text": $(echo "$prompt" | jq -Rs .)
        },
        {
          "type": "image_url",
          "image_url": {
            "url": "data:image/png;base64,$image_base64"
          }
        }
      ]
    }
  ],
  "max_tokens": 2000
}
EOF
    
    # 检查临时文件是否存在
    if [[ ! -f "$temp_json" ]]; then
        log_error "临时 JSON 文件创建失败: $temp_json"
        return 1
    fi
    
    log_debug "发送 API 请求到 302 平台..."
    log_debug "临时文件内容预览: $(head -c 200 "$temp_json")..."
    local api_start_time=$(date +%s.%N)
    local response=$(curl -s -w "\nHTTP_CODE:%{http_code}\nTIME:%{time_total}" -X POST "https://api.302.ai/v1/chat/completions" \
      -H "Authorization: Bearer $PLATFORM302_API_KEY" \
      -H "Content-Type: application/json" \
      -d "@$temp_json" 2>&1)
    local api_end_time=$(date +%s.%N)
    local api_duration=$(echo "$api_end_time - $api_start_time" | bc)
    
    # 提取 HTTP 状态码和响应时间
    local http_code=$(echo "$response" | grep "HTTP_CODE:" | cut -d: -f2)
    local response_time=$(echo "$response" | grep "TIME:" | cut -d: -f2)
    local response_body=$(echo "$response" | sed '/HTTP_CODE:/d' | sed '/TIME:/d')
    
    log_debug "API 响应时间: ${api_duration}s, HTTP 状态码: $http_code, 响应时间: ${response_time}s"
    log_debug "响应体长度: ${#response_body} 字符"
    
    # 清理临时文件
    rm -f "$temp_json" 2>/dev/null || true
    
    # 检查 HTTP 状态码
    if [[ "$http_code" != "200" ]] && [[ -n "$http_code" ]]; then
        log_error "API 返回非 200 状态码: $http_code, 响应: $(echo "$response_body" | head -500)"
        return 1
    fi
    
    # 检查响应中是否有错误字段（不是包含 "error" 字符串，而是 JSON 中的 error 字段）
    if echo "$response_body" | jq -e '.error' >/dev/null 2>&1; then
        local error_msg=$(echo "$response_body" | jq -r '.error.message // .error // "Unknown error"' 2>/dev/null)
        log_error "API 返回错误: $error_msg"
        log_debug "完整错误响应: $(echo "$response_body" | head -500)"
        return 1
    fi
    
    # 检查 jq 是否可用
    if ! command -v jq >/dev/null 2>&1; then
        log_error "未找到 jq 命令，无法解析响应"
        return 1
    fi
    
    # 尝试获取 content，如果没有则尝试 reasoning_content
    log_debug "解析 API 响应..."
    local analysis=$(echo "$response_body" | jq -r '.choices[0].message.content // .choices[0].message.reasoning_content // empty' 2>/dev/null)
    if [[ -z "$analysis" ]] || [[ "$analysis" == "null" ]]; then
        log_error "响应解析失败"
        log_debug "原始响应前 500 字符: $(echo "$response_body" | head -c 500)"
        log_debug "尝试检查响应结构: $(echo "$response_body" | jq 'keys' 2>/dev/null || echo "无法解析 JSON")"
        return 1
    fi
    
    local analysis_length=${#analysis}
    log_info "✅ 分析完成，内容长度: $analysis_length 字符"
    log_debug "分析内容预览: $(echo "$analysis" | head -c 200)..."
    
    echo "$analysis"
}

# 找到聊天框元素ID（用于滚动）
find_chat_element() {
    log_debug "查找 Cursor 聊天框元素..."
    
    # 聚焦 Cursor 窗口
    peekaboo window focus --app "$CURSOR_APP" 2>/dev/null || true
    sleep 0.3
    
    # 使用 peekaboo see 找到聊天区域元素（优先找 scrollArea）
    local see_output=$(peekaboo see --app "$CURSOR_APP" --json 2>/dev/null 2>&1)
    local chat_element=""
    
    if echo "$see_output" | jq -e '.data.elements' >/dev/null 2>&1; then
        chat_element=$(echo "$see_output" | \
            jq -r '.data.elements[]? | 
                select((.role == "scrollArea" or .type == "scrollView") and 
                       ((.frame.width // 0 | tonumber) > 200) and 
                       ((.frame.height // 0 | tonumber) > 300)) | 
                .id' 2>/dev/null | head -1)
    fi
    
    if [[ -n "$chat_element" ]] && [[ "$chat_element" != "null" ]]; then
        log_info "✅ 找到聊天区域元素: $chat_element"
        echo "$chat_element"
        return 0
    fi
    
    # 如果找不到 scrollArea，尝试找大的 group 元素（通常在右侧）
    if [[ -z "$chat_element" ]] || [[ "$chat_element" == "null" ]]; then
        if echo "$see_output" | jq -e '.data.elements' >/dev/null 2>&1; then
            chat_element=$(echo "$see_output" | \
                jq -r '.data.elements[]? | 
                    select(.role == "group" and 
                           ((.frame.width // 0 | tonumber) > 300) and 
                           ((.frame.height // 0 | tonumber) > 400) and
                           ((.frame.x // 0 | tonumber) > 500)) | 
                    .id' 2>/dev/null | head -1)
        fi
    fi
    
    if [[ -n "$chat_element" ]] && [[ "$chat_element" != "null" ]]; then
        log_info "✅ 找到可能的聊天区域元素: $chat_element"
        echo "$chat_element"
        return 0
    fi
    
    log_warn "未找到聊天元素，将使用坐标方式"
    echo ""
    return 1
}

# 使用智能方式滚动（Python + AI 识别）
scroll_one_page_up_smart() {
    log_info "🤖 使用 AI 视觉识别定位聊天框并滚动..."
    
    # 调用 Python 脚本进行智能滚动
    if command -v python3 >/dev/null 2>&1; then
        log_info "📜 开始智能滚动（大幅慢速，便于观察）..."
        local result=$(python3 /Users/oscar/moltbot/cursor_smart_scroll.py 2>&1)
        
        # 提取关键信息
        local scroll_method=$(echo "$result" | grep -E "使用方式:|Peekaboo|macOS 原生" | head -1)
        local scroll_status=$(echo "$result" | grep -E "✅|❌|⚠️" | tail -1)
        
        # 记录详细日志
        echo "$result" | while IFS= read -r line; do
            if echo "$line" | grep -qE "使用方式:|滚动完成|滚动失败|截图已变化"; then
                log_info "$line"
            elif echo "$line" | grep -qE "✅|❌|⚠️|📊|📜|🎯"; then
                log_debug "$line"
            fi
        done
        
        if echo "$result" | grep -q "滚动完成"; then
            log_info "✅ 智能滚动成功 - $scroll_method"
            return 0
        else
            log_warn "智能滚动失败，回退到传统方式"
        fi
    else
        log_warn "未找到 python3，回退到传统方式"
    fi
    
    # 回退到传统方式
    scroll_one_page_up_traditional
}

# 传统滚动方式（保留作为备选）
scroll_one_page_up_traditional() {
    # 先截图记录滚动前状态
    local before_screenshot="/tmp/scroll_before_$$.png"
    peekaboo image --app "$CURSOR_APP" --mode window --path "$before_screenshot" 2>/dev/null
    local before_hash=""
    if [[ -f "$before_screenshot" ]]; then
        before_hash=$(md5 -q "$before_screenshot" 2>/dev/null || echo "")
    fi
    
    # 找到聊天框元素
    local chat_element=$(find_chat_element)
    
    if [[ -n "$chat_element" ]] && [[ "$chat_element" != "null" ]]; then
        # 先点击聚焦到聊天框
        peekaboo click --on "$chat_element" --app "$CURSOR_APP" 2>/dev/null || true
        sleep 0.3
        
        # 在聊天框元素上滚动
        log_debug "在聊天框元素 ($chat_element) 上向上滚动..."
        if peekaboo scroll --app "$CURSOR_APP" --on "$chat_element" --direction up --amount 5 --smooth 2>/dev/null; then
            log_debug "✅ 在聊天框元素上滚动成功"
        else
            log_debug "元素滚动失败，尝试窗口滚动..."
            peekaboo scroll --app "$CURSOR_APP" --direction up --amount 5 --smooth 2>/dev/null || true
        fi
    else
        # 如果找不到元素，使用坐标方式
        log_debug "使用坐标方式定位聊天区域..."
        local window_info=$(peekaboo list windows --app "$CURSOR_APP" --json 2>/dev/null)
        if [[ -n "$window_info" ]]; then
            local window_bounds=$(echo "$window_info" | jq -r '.data.windows[0].bounds // empty' 2>/dev/null)
            if [[ -n "$window_bounds" ]]; then
                local window_width=$(echo "$window_bounds" | jq -r '.[1][0]' 2>/dev/null)
                local window_height=$(echo "$window_bounds" | jq -r '.[1][1]' 2>/dev/null)
                local chat_x=$(echo "$window_width * 0.75" | bc 2>/dev/null || echo "1000")
                local chat_y=$(echo "$window_height * 0.5" | bc 2>/dev/null || echo "500")
                
                # 点击聊天区域聚焦
                peekaboo click --coords "${chat_x},${chat_y}" --app "$CURSOR_APP" 2>/dev/null || true
                sleep 0.3
                
                # 在聊天区域滚动
                log_debug "在聊天区域坐标 (${chat_x},${chat_y}) 上滚动..."
                peekaboo scroll --app "$CURSOR_APP" --direction up --amount 5 --smooth 2>/dev/null || true
            fi
        fi
    fi
    
    sleep 0.8  # 等待滚动完成
    
    # 检查是否真的滚动了（比较截图）
    local after_screenshot="/tmp/scroll_after_$$.png"
    peekaboo image --app "$CURSOR_APP" --mode window --path "$after_screenshot" 2>/dev/null
    local scroll_worked=false
    
    if [[ -f "$after_screenshot" ]]; then
        local after_hash=$(md5 -q "$after_screenshot" 2>/dev/null || echo "")
        if [[ -n "$before_hash" ]] && [[ "$before_hash" != "$after_hash" ]]; then
            log_info "✅ 滚动生效（截图已变化）"
            scroll_worked=true
        else
            log_debug "⚠️  滚动后截图未变化（可能已到顶部或内容相同）"
        fi
    fi
    
    # 清理临时截图
    rm -f /tmp/scroll_*.png 2>/dev/null || true
    
    if [ "$scroll_worked" = true ]; then
        return 0
    else
        # 即使截图未变化，也返回成功（可能是已到顶部）
        return 0
    fi
}

# 执行 Cursor 操作
execute_cursor_action() {
    local action="$1"
    
    log "🎮 执行 Cursor 操作: $action"
    
    # 聚焦 Cursor 窗口
    peekaboo window focus --app "$CURSOR_APP" 2>/dev/null || true
    sleep 0.5
    
    case "$action" in
        pause|stop)
            # 在聊天框中输入 /stop 或 Ctrl+C
            peekaboo click --app "$CURSOR_APP" --coords "400,800" 2>/dev/null || true
            sleep 0.3
            peekaboo type "/stop" --app "$CURSOR_APP" --delay 10 2>/dev/null || true
            sleep 0.3
            peekaboo press return --app "$CURSOR_APP" 2>/dev/null || true
            log "✅ 已发送暂停命令"
            ;;
        *)
            log "⚠️  未知操作: $action"
            ;;
    esac
}

# 判断是否需要通知
should_notify() {
    local analysis="$1"
    local previous_analysis="${2:-}"
    
    # 检查关键词，判断是否真的卡住或有问题
    local urgent_keywords=("卡住" "错误" "失败" "超时" "异常" "无法" "需要人工干预" "思路偏差" "理解错误")
    local normal_keywords=("正在思考" "正在生成" "进行中" "正常" "已完成")
    
    # 如果分析中提到卡住或错误
    for keyword in "${urgent_keywords[@]}"; do
        if echo "$analysis" | grep -qi "$keyword"; then
            log "🔴 检测到紧急关键词: $keyword"
            return 0  # 需要通知
        fi
    done
    
    # 如果内容长时间未变化，且不是正常状态
    if [[ -n "$previous_analysis" ]]; then
        # 比较两次分析，如果状态相同且不是"正常进行中"，可能需要通知
        if echo "$analysis" | grep -qi "等待\|暂停\|停止" && echo "$previous_analysis" | grep -qi "等待\|暂停\|停止"; then
            log "⚠️  状态持续异常"
            return 0  # 需要通知
        fi
    fi
    
    # 默认不通知（保守策略）
    return 1
}

# 发送 WhatsApp 通知
send_whatsapp_notification() {
    local message="$1"
    local screenshot_path="${2:-}"
    
    log "📱 发送 WhatsApp 通知..."
    
    # 构建完整的通知消息
    local full_message="🤖 Cursor 智能监控报告

$message

---
时间: $(date '+%Y-%m-%d %H:%M:%S')
如需停止监控，请发送命令：/stop-monitor"

    # 通过 Gateway 发送
    local response=$(curl -s -X POST "$GATEWAY_URL/rpc/send" \
      -H "Authorization: Bearer $GATEWAY_TOKEN" \
      -H "Content-Type: application/json" \
      -d "{
        \"channel\": \"whatsapp\",
        \"to\": \"$WHATSAPP_TARGET\",
        \"message\": $(echo "$full_message" | jq -Rs .)
      }" 2>&1) || {
        log "⚠️  发送失败，尝试使用 CLI..."
        cd /Users/oscar/moltbot/openclaw && \
        pnpm openclaw gateway call send \
            --params "{\"channel\":\"whatsapp\",\"to\":\"$WHATSAPP_TARGET\",\"message\":$(echo "$full_message" | jq -Rs .)}" \
            2>&1 | tee -a "$LOG_FILE" || true
    }
    
    log "✅ 通知已发送"
}

# 主监控循环
main_loop() {
    log "🚀 启动 Cursor 智能监控..."
    log "监控间隔: ${INTERVAL}秒"
    log "WhatsApp 目标: $WHATSAPP_TARGET"
    
    local last_analysis=""
    local last_analysis_time=0
    local consecutive_issues=0
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
        log_debug "开始截取 Cursor 窗口..."
        local screenshot=$(capture_cursor_window)
        local screenshot_exit=$?
        log_debug "截图函数退出码: $screenshot_exit, 返回路径: $screenshot"
        
        if [ $screenshot_exit -ne 0 ] || [[ -z "$screenshot" ]] || [[ ! -f "$screenshot" ]]; then
            log_warn "截图失败，退出码: $screenshot_exit, 路径: $screenshot"
            if [[ -n "$screenshot" ]]; then
                log_debug "检查文件状态: $(ls -lh "$screenshot" 2>&1 || echo "文件不存在")"
            fi
            sleep $INTERVAL
            continue
        fi
        
        log_info "✅ 截图成功，继续分析: $screenshot"
        
        # 智能分析（先分析当前状态，再根据需要查看历史记录）
        log_info "🔍 开始智能分析..."
        
        # 先分析当前截图
        local analysis=$(analyze_screenshot_intelligently "$screenshot" "$last_analysis")
        
        # 如果分析失败或检测到问题，才查看历史记录
        local history_summary=""
        if [[ -z "$analysis" ]] || [[ "$analysis" == *"失败"* ]] || echo "$analysis" | grep -qi "卡住\|错误\|失败\|需要人工干预"; then
            log_info "📜 检测到问题，查看历史聊天记录以获取上下文..."
            
            # 智能滚动查看历史记录（最多3页，如果发现无关就停止）
            local history_screenshots=()
            local max_scrolls=3
            local scroll_count=0
            
            for i in $(seq 1 $max_scrolls); do
                # 向上滚动一页（使用智能方式）
                log_info "📜 向上滚动第 $i 页查看历史记录..."
                if scroll_one_page_up_smart; then
                    scroll_count=$((scroll_count + 1))
                    sleep 2  # 等待滚动完成，确保内容加载
                    
                    # 截图并分析（重要：记录滚动查看的内容）
                    log_info "📸 截图并分析第 $i 页历史记录内容..."
                    local hist_screenshot=$(capture_cursor_window)
                    if [[ -f "$hist_screenshot" ]]; then
                        history_screenshots+=("$hist_screenshot")
                        
                        # 详细分析这一页的内容（不是快速分析，要完整记录）
                        log_info "🔍 使用 AI 分析第 $i 页历史记录内容..."
                        local page_analysis=$(analyze_screenshot_intelligently "$hist_screenshot" "" 2>/dev/null)
                        
                        if [[ -n "$page_analysis" ]] && [[ "$page_analysis" != *"失败"* ]]; then
                            # 记录这一页的完整分析内容
                            log_info "✅ 第 $i 页分析完成，内容长度: ${#page_analysis} 字符"
                            log_debug "第 $i 页内容预览: $(echo "$page_analysis" | head -c 200)..."
                            
                            # 将这一页的分析添加到历史总结中（无论是否相关，先记录下来）
                            history_summary="$history_summary\n\n**历史记录第 $i 页（向上滚动查看）：**\n$page_analysis"
                            
                            # 判断是否与当前问题相关
                            log_debug "判断第 $i 页历史记录是否与当前问题相关..."
                            
                            # 使用关键词检测判断相关性
                            local is_relevant=false
                            if echo "$page_analysis" | grep -qiE "用户.*问题|用户.*问|错误|失败|卡住|当前|刚才|最近|相关|上下文|任务|需求"; then
                                is_relevant=true
                            fi
                            
                            if [ "$is_relevant" = true ]; then
                                log_info "✅ 第 $i 页历史记录与当前问题相关，继续查看..."
                            else
                                log_info "ℹ️  第 $i 页历史记录与当前问题无关，停止向上滚动"
                                log_info "📝 已记录 $scroll_count 页历史记录内容，将包含在报告中"
                                break
                            fi
                        else
                            log_warn "⚠️  第 $i 页分析失败，但继续记录截图"
                        fi
                    else
                        log_warn "⚠️  第 $i 页截图失败"
                    fi
                else
                    log_warn "滚动失败，停止查看历史记录"
                    break
                fi
            done
            
            log_info "📜 共查看了 $scroll_count 页历史记录"
            
            # 汇总所有历史记录内容
            if [[ -n "$history_summary" ]]; then
                log_info "📚 已记录所有查看的历史记录内容，将包含在分析报告中"
                log_debug "历史记录总结长度: ${#history_summary} 字符"
            else
                log_warn "⚠️  未记录到历史记录内容"
            fi
            
            # 不滚回到底部，保持当前查看位置
        fi
        
        if [[ -z "$analysis" ]] || [[ "$analysis" == *"失败"* ]]; then
            log "⚠️  分析失败，跳过本次检查"
            sleep $INTERVAL
            continue
        fi
        
        # 保存分析结果
        echo "$analysis" > "$STATE_DIR/last_analysis.txt"
        last_analysis="$analysis"
        last_analysis_time=$(date +%s)
        
        # 判断是否需要通知（使用更新前的 last_analysis 作为对比）
        local previous_analysis_for_notify="$last_analysis"
        if should_notify "$analysis" "$previous_analysis_for_notify"; then
            consecutive_issues=$((consecutive_issues + 1))
            log "⚠️  检测到问题 (连续: $consecutive_issues 次)"
            
            # 如果连续检测到问题，且距离上次通知超过冷却时间
            local current_time=$(date +%s)
            if [[ $consecutive_issues -ge 2 ]] && [[ $((current_time - last_notification_time)) -gt $notification_cooldown ]]; then
                log "🔔 触发智能通知..."
                
                # 构建详细报告（包含历史记录总结）
                local report="## 📊 Cursor 智能监控报告

### 🔍 当前状态分析
$analysis

### 📜 历史记录上下文（通过滚动查看并分析）
$(if [[ -n "$history_summary" ]]; then
    echo -e "$history_summary"
    echo ""
    echo "**说明：** 以上是通过向上滚动查看的 $scroll_count 页历史聊天记录，已使用 AI 完整分析并记录。这些内容用于理解当前问题的上下文。"
else
    echo "（未查看历史记录或历史记录为空）"
fi)

### 📈 统计信息
- **连续检测到问题次数：** $consecutive_issues 次
- **查看的历史记录页数：** $scroll_count 页
- **检测时间：** $(date '+%Y-%m-%d %H:%M:%S')

### 🎯 请选择操作
回复以下命令：
- **继续** 或 **1** - 继续监控，忽略此次通知
- **暂停** 或 **2** - 暂停当前任务
- **修改** 或 **3** - 我来调整对话方向
- **查看** 或 **4** - 查看更详细的历史记录"
                
                send_whatsapp_notification "$report" "$screenshot"
                last_notification_time=$current_time
                consecutive_issues=0  # 重置计数
                
                # 等待用户回复（最多等待 5 分钟）
                log "⏳ 等待用户 WhatsApp 回复..."
                local wait_start=$(date +%s)
                local wait_timeout=300  # 5分钟
                local user_replied=false
                
                while [[ $((current_time - wait_start)) -lt $wait_timeout ]]; do
                    sleep 10  # 每10秒检查一次
                    current_time=$(date +%s)
                    
                    # 检查是否有新的 WhatsApp 消息（通过 Gateway）
                    # 这里需要实现消息监听，暂时简化处理
                    # TODO: 实现真正的消息监听
                    
                    # 临时方案：检查是否有回复文件
                    if [[ -f "$STATE_DIR/user_reply.txt" ]]; then
                        local user_reply=$(cat "$STATE_DIR/user_reply.txt" 2>/dev/null | tr '[:upper:]' '[:lower:]' | tr -d ' ')
                        rm -f "$STATE_DIR/user_reply.txt"
                        
                        log "📩 收到用户回复: $user_reply"
                        
                        case "$user_reply" in
                            *继续*|*1*|*continue*|*ignore*)
                                log "✅ 用户选择：继续监控"
                                user_replied=true
                                break
                                ;;
                            *暂停*|*2*|*pause*|*stop*)
                                log "⏸️  用户选择：暂停任务"
                                # 执行暂停操作
                                execute_cursor_action "pause"
                                user_replied=true
                                break
                                ;;
                            *修改*|*3*|*modify*|*adjust*)
                                log "✏️  用户选择：修改对话方向"
                                # 等待用户输入具体指令
                                log "⏳ 等待用户输入具体修改指令..."
                                user_replied=true
                                break
                                ;;
                            *查看*|*4*|*view*|*history*)
                                log_info "📜 用户选择：查看历史记录"
                                # 滚动查看更多历史记录（最多3页）
                                local more_history_screenshots=()
                                for j in $(seq 1 3); do
                                    if scroll_one_page_up; then
                                        sleep 1.5
                                        local more_hist=$(capture_cursor_window)
                                        if [[ -f "$more_hist" ]]; then
                                            more_history_screenshots+=("$more_hist")
                                        fi
                                    fi
                                done
                                
                                # 分析所有历史截图
                                local more_history_summary="## 📜 历史记录详情\n\n"
                                for hist_img in "${more_history_screenshots[@]}"; do
                                    local more_analysis=$(analyze_screenshot_intelligently "$hist_img" "" 2>/dev/null)
                                    if [[ -n "$more_analysis" ]] && [[ "$more_analysis" != *"失败"* ]]; then
                                        more_history_summary="$more_history_summary\n**历史记录片段：**\n$more_analysis\n\n"
                                    fi
                                done
                                
                                send_whatsapp_notification "$more_history_summary" "${more_history_screenshots[0]}"
                                user_replied=true
                                break
                                ;;
                            *)
                                log "⚠️  未识别的回复，继续等待..."
                                ;;
                        esac
                    fi
                done
                
                if [[ "$user_replied" = false ]]; then
                    log "⏰ 等待超时，继续监控"
                fi
            fi
        else
            # 状态正常，重置计数
            if [[ $consecutive_issues -gt 0 ]]; then
                log "✅ 状态恢复正常"
                consecutive_issues=0
            else
                log "✅ 状态正常"
            fi
        fi
        
        # 等待下次检查
        sleep $INTERVAL
    done
}

# 启动函数
start_monitoring() {
    log "=========================================="
    log "Cursor IDE 智能监控启动"
    log "=========================================="
    
    # 检查依赖
    if ! command -v peekaboo >/dev/null 2>&1 && ! command -v screencapture >/dev/null 2>&1; then
        log "❌ 错误：未找到截图工具（peekaboo 或 screencapture）"
        exit 1
    fi
    
    if ! command -v jq >/dev/null 2>&1; then
        log "❌ 错误：未找到 jq 命令，请安装: brew install jq"
        exit 1
    fi
    
    if ! command -v base64 >/dev/null 2>&1; then
        log "❌ 错误：未找到 base64 命令"
        exit 1
    fi
    
    # 启动主循环
    main_loop
}

# 主函数
case "${1:-start}" in
    start)
        start_monitoring
        ;;
    stop)
        log "停止监控..."
        pkill -f "cursor_smart_monitor.sh" || true
        ;;
    status)
        if pgrep -f "cursor_smart_monitor.sh" > /dev/null; then
            echo "✅ 监控正在运行"
            tail -20 "$LOG_FILE"
        else
            echo "❌ 监控未运行"
        fi
        ;;
    *)
        echo "用法: $0 [start|stop|status]"
        exit 1
        ;;
esac
