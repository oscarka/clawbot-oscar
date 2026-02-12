#!/bin/bash

# OpenClaw 监控命令集成
# 提供 /monitor-start 和 /monitor-stop 命令

MONITOR_SCRIPT="/Users/oscar/moltbot/cursor_smart_monitor.sh"
LOG_FILE="$HOME/.openclaw/cursor_smart_monitor.log"

case "${1:-}" in
    start|on|enable)
        if pgrep -f "cursor_smart_monitor.sh" > /dev/null; then
            echo "⚠️  监控已在运行中"
            exit 0
        fi
        
        echo "🚀 启动 Cursor 智能监控..."
        nohup bash "$MONITOR_SCRIPT" start > "$LOG_FILE" 2>&1 &
        echo "✅ 监控已启动（后台运行）"
        echo "📋 查看日志: tail -f $LOG_FILE"
        ;;
    stop|off|disable)
        if ! pgrep -f "cursor_smart_monitor.sh" > /dev/null; then
            echo "⚠️  监控未运行"
            exit 0
        fi
        
        echo "⏸️  停止 Cursor 智能监控..."
        pkill -f "cursor_smart_monitor.sh"
        sleep 1
        if ! pgrep -f "cursor_smart_monitor.sh" > /dev/null; then
            echo "✅ 监控已停止"
        else
            echo "⚠️  停止失败，请手动检查"
        fi
        ;;
    status|info)
        if pgrep -f "cursor_smart_monitor.sh" > /dev/null; then
            echo "✅ 监控状态: 运行中"
            echo ""
            echo "📋 最近日志:"
            tail -10 "$LOG_FILE" 2>/dev/null || echo "  无日志"
        else
            echo "❌ 监控状态: 未运行"
        fi
        ;;
    *)
        echo "用法: $0 [start|stop|status]"
        echo ""
        echo "命令："
        echo "  start  - 启动智能监控"
        echo "  stop   - 停止智能监控"
        echo "  status - 查看监控状态"
        exit 1
        ;;
esac
