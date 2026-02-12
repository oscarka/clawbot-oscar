#!/bin/bash
# 监控状态文件，在显眼位置显示状态

STATUS_FILE="/tmp/vision_agent_status.txt"
LOG_FILE="/tmp/vision_agent_status.log"

echo "📊 Vision Agent 状态监控"
echo "状态文件: $STATUS_FILE"
echo "日志文件: $LOG_FILE"
echo "按 Ctrl+C 退出"
echo ""

# 持续监控状态文件
while true; do
    clear
    echo "═══════════════════════════════════════════════════════════"
    echo "📊 Vision Agent 实时状态"
    echo "═══════════════════════════════════════════════════════════"
    echo ""
    
    if [ -f "$STATUS_FILE" ]; then
        cat "$STATUS_FILE"
    else
        echo "⚠️  状态文件不存在，等待中..."
    fi
    
    echo ""
    echo "═══════════════════════════════════════════════════════════"
    echo "📝 最近日志（最后 10 行）"
    echo "═══════════════════════════════════════════════════════════"
    if [ -f "$LOG_FILE" ]; then
        tail -10 "$LOG_FILE"
    else
        echo "暂无日志"
    fi
    
    echo ""
    echo "更新时间: $(date '+%Y-%m-%d %H:%M:%S')"
    echo "按 Ctrl+C 退出监控"
    
    sleep 2
done
