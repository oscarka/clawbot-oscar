#!/bin/bash

# Cursor IDE 自动化操作脚本
# 功能：根据用户确认，在 Cursor IDE 中执行点击、输入等操作
# 使用方法：cursor_automation.sh <action> [options]

set -euo pipefail

CURSOR_APP="Cursor"
LOG_FILE="$HOME/.openclaw/cursor_automation.log"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# 检查 Cursor 是否运行
ensure_cursor_running() {
    if ! peekaboo list apps --json 2>/dev/null | grep -qi "\"$CURSOR_APP\""; then
        log "❌ Cursor 未运行，尝试启动..."
        open -a "$CURSOR_APP" 2>/dev/null || {
            log "❌ 无法启动 Cursor"
            exit 1
        }
        sleep 3
    fi
}

# 聚焦 Cursor 窗口
focus_cursor() {
    log "聚焦 Cursor 窗口..."
    peekaboo window focus --app "$CURSOR_APP" 2>&1 | tee -a "$LOG_FILE" || true
    sleep 1
}

# 在聊天输入框中输入文本
type_in_chat() {
    local text="$1"
    log "在聊天框中输入: $text"
    
    # 先尝试找到聊天输入框（可能需要先截图识别）
    local screenshot=$(mktemp /tmp/cursor_chat_XXXXXX.png)
    peekaboo see --app "$CURSOR_APP" --annotate --path "$screenshot" 2>&1 | tee -a "$LOG_FILE" || true
    
    # 尝试点击聊天输入区域（通常在下半部分）
    # 这里需要根据实际 UI 调整坐标或元素 ID
    peekaboo click --app "$CURSOR_APP" --coords "400,800" 2>&1 | tee -a "$LOG_FILE" || true
    sleep 0.5
    
    # 输入文本
    peekaboo type "$text" --app "$CURSOR_APP" --delay 10 2>&1 | tee -a "$LOG_FILE" || true
    sleep 0.5
    
    # 按回车发送
    peekaboo press return --app "$CURSOR_APP" 2>&1 | tee -a "$LOG_FILE" || true
    
    rm -f "$screenshot"
}

# 暂停当前对话（发送停止命令）
pause_chat() {
    log "⏸️  暂停对话..."
    focus_cursor
    
    # 尝试发送 Ctrl+C 或 Escape
    peekaboo hotkey --keys "cmd,." --app "$CURSOR_APP" 2>&1 | tee -a "$LOG_FILE" || true
    # 或者
    peekaboo press escape --app "$CURSOR_APP" 2>&1 | tee -a "$LOG_FILE" || true
}

# 修改对话方向（输入新指令）
modify_chat() {
    local instruction="$1"
    log "✏️  修改对话方向: $instruction"
    
    focus_cursor
    
    # 先暂停当前对话
    pause_chat
    sleep 1
    
    # 输入新指令
    type_in_chat "$instruction"
}

# 继续对话（发送继续指令）
continue_chat() {
    log "▶️  继续对话..."
    focus_cursor
    type_in_chat "请继续"
}

# 主函数
main() {
    local action="${1:-help}"
    
    case "$action" in
        pause)
            ensure_cursor_running
            pause_chat
            ;;
        modify)
            local instruction="${2:-请调整对话方向}"
            ensure_cursor_running
            modify_chat "$instruction"
            ;;
        continue)
            ensure_cursor_running
            continue_chat
            ;;
        type)
            local text="${2:-}"
            if [[ -z "$text" ]]; then
                log "❌ 错误：需要提供要输入的文本"
                exit 1
            fi
            ensure_cursor_running
            focus_cursor
            type_in_chat "$text"
            ;;
        focus)
            ensure_cursor_running
            focus_cursor
            ;;
        help|*)
            echo "用法: $0 <action> [options]"
            echo ""
            echo "操作:"
            echo "  pause              - 暂停当前对话"
            echo "  modify <instruction> - 修改对话方向（输入新指令）"
            echo "  continue           - 继续对话"
            echo "  type <text>        - 在聊天框中输入文本"
            echo "  focus              - 聚焦 Cursor 窗口"
            echo ""
            echo "示例:"
            echo "  $0 pause"
            echo "  $0 modify '请改用更简单的方法'"
            echo "  $0 type '你好，请继续'"
            exit 1
            ;;
    esac
}

main "$@"
