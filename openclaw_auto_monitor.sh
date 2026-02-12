#!/bin/bash

# OpenClaw 自动监控和修复脚本
# 使用方法：添加到 crontab，每 5 分钟执行一次
# */5 * * * * /Users/oscar/moltbot/openclaw_auto_monitor.sh >> ~/.openclaw/monitor.log 2>&1

LOG_FILE="$HOME/.openclaw/monitor.log"
GATEWAY_LOG="$HOME/.openclaw/logs/gateway.log"
GATEWAY_ERR_LOG="$HOME/.openclaw/logs/gateway.err.log"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

# 阈值配置
AGENT_WAIT_WARNING=60      # 60秒警告
AGENT_WAIT_CRITICAL=120    # 120秒自动停止
GATEWAY_NO_RESPONSE=30      # 30秒无响应重启
MAX_CONSECUTIVE_TIMEOUTS=3  # 连续3次超时重置会话

log_message() {
    echo "[$TIMESTAMP] $1" >> "$LOG_FILE"
}

# 检查 Gateway 进程
check_gateway_process() {
    if ! pgrep -f "openclaw-gateway" > /dev/null; then
        log_message "⚠️ Gateway 进程不存在，尝试启动..."
        launchctl load ~/Library/LaunchAgents/ai.openclaw.gateway.plist 2>/dev/null
        sleep 5
        if pgrep -f "openclaw-gateway" > /dev/null; then
            log_message "✅ Gateway 已启动"
        else
            log_message "❌ Gateway 启动失败"
        fi
        return 1
    fi
    return 0
}

# 检查 Gateway 响应
check_gateway_response() {
    if ! curl -s http://127.0.0.1:18789/health > /dev/null 2>&1; then
        log_message "⚠️ Gateway 无响应，检查日志..."
        return 1
    fi
    return 0
}

# 检查是否有活动迹象（最近5分钟内有日志更新）
check_recent_activity() {
    if [ ! -f "$GATEWAY_LOG" ]; then
        return 1
    fi
    
    local last_log_time=$(stat -f %m "$GATEWAY_LOG" 2>/dev/null || echo 0)
    local now=$(date +%s)
    local age=$((now - last_log_time))
    
    # 如果日志文件最近5分钟内有更新，说明有活动
    if [ $age -lt 300 ]; then
        return 0
    fi
    return 1
}

# 检查是否有工具调用或流式输出（表示正在处理）
check_processing_indicators() {
    if [ ! -f "$GATEWAY_LOG" ]; then
        return 1
    fi
    
    # 检查最近5分钟内的活动迹象
    local recent_activity=$(tail -200 "$GATEWAY_LOG" | grep -E "tool|stream|assistant|lifecycle" | tail -1)
    
    if [ -n "$recent_activity" ]; then
        # 检查这条日志的时间戳
        local log_time=$(echo "$recent_activity" | grep -oE "[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}" | head -1)
        if [ -n "$log_time" ]; then
            # 转换为时间戳并检查是否在最近5分钟内
            local log_timestamp=$(date -j -f "%Y-%m-%dT%H:%M:%S" "$log_time" +%s 2>/dev/null || echo 0)
            local now=$(date +%s)
            local age=$((now - log_timestamp))
            
            if [ $age -lt 300 ] && [ $log_timestamp -gt 0 ]; then
                return 0  # 有活动迹象
            fi
        fi
    fi
    
    return 1
}

# 检查卡住的任务（改进版：区分卡顿和处理中）
check_stuck_tasks() {
    if [ ! -f "$GATEWAY_LOG" ]; then
        return 0
    fi
    
    # 首先检查 OpenClaw 自己标记的 "stuck session"
    local stuck_sessions=$(tail -100 "$GATEWAY_LOG" | grep -c "stuck session")
    if [ $stuck_sessions -gt 0 ]; then
        log_message "🚨 检测到 OpenClaw 标记的卡住会话，自动停止..."
        cd /Users/oscar/moltbot/openclaw
        source ~/.nvm/nvm.sh && nvm use 22 2>/dev/null
        # 通过 Gateway CLI 发送中止命令
        pnpm openclaw gateway call chat.abort --params '{"sessionKey":"agent:main:main"}' > /dev/null 2>&1
        log_message "✅ 已发送停止命令"
        return 1
    fi
    
    # 检查最近的 agent.wait 时间
    local last_wait=$(tail -100 "$GATEWAY_LOG" | grep "agent.wait" | tail -1 | grep -oE "[0-9]+ms" | grep -oE "[0-9]+")
    
    if [ -n "$last_wait" ]; then
        local wait_seconds=$((last_wait / 1000))
        
        # 如果等待时间超过阈值，检查是否有活动迹象
        if [ $wait_seconds -gt $AGENT_WAIT_CRITICAL ]; then
            # 检查是否有处理中的迹象
            if check_processing_indicators; then
                log_message "ℹ️ agent.wait ${wait_seconds}秒，但检测到活动迹象，可能是正常处理中，继续观察..."
                return 0
            elif check_recent_activity; then
                log_message "ℹ️ agent.wait ${wait_seconds}秒，但日志最近有更新，继续观察..."
                return 0
            else
                # 没有活动迹象，确实是卡住了
                log_message "🚨 检测到严重卡顿：agent.wait ${wait_seconds}秒且无活动迹象，自动停止..."
                cd /Users/oscar/moltbot/openclaw
                source ~/.nvm/nvm.sh && nvm use 22 2>/dev/null
                # 通过 Gateway CLI 发送中止命令
                pnpm openclaw gateway call chat.abort --params '{"sessionKey":"agent:main:main"}' > /dev/null 2>&1
                log_message "✅ 已发送停止命令"
                return 1
            fi
        elif [ $wait_seconds -gt $AGENT_WAIT_WARNING ]; then
            # 检查是否有处理中的迹象
            if check_processing_indicators || check_recent_activity; then
                log_message "ℹ️ agent.wait ${wait_seconds}秒，但检测到活动，可能是正常处理中"
            else
                log_message "⚠️ 检测到潜在卡顿：agent.wait ${wait_seconds}秒且无活动迹象"
            fi
        fi
    fi
    
    # 检查连续超时（这些通常是真正的错误）
    local timeout_count=$(tail -50 "$GATEWAY_LOG" | grep -c "timeout\|Timeout\|TIMEOUT")
    if [ $timeout_count -ge $MAX_CONSECUTIVE_TIMEOUTS ]; then
        log_message "🚨 检测到连续超时（${timeout_count}次），重置会话..."
        cd /Users/oscar/moltbot/openclaw
        source ~/.nvm/nvm.sh && nvm use 22 2>/dev/null
        # 通过 Gateway CLI 重置会话
        pnpm openclaw gateway call sessions.reset --params '{"key":"agent:main:main"}' > /dev/null 2>&1
        log_message "✅ 已重置会话"
        return 1
    fi
    
    return 0
}

# 检查错误日志
check_error_logs() {
    if [ ! -f "$GATEWAY_ERR_LOG" ]; then
        return 0
    fi
    
    local recent_errors=$(tail -20 "$GATEWAY_ERR_LOG" | grep -c "error\|Error\|ERROR\|failed\|Failed")
    
    if [ $recent_errors -gt 10 ]; then
        log_message "⚠️ 检测到大量错误（${recent_errors}条），建议检查"
    fi
    
    return 0
}

# 清理锁文件
cleanup_locks() {
    local cleaned=0
    
    if [ -f "$HOME/.openclaw/.gateway.lock" ]; then
        local lock_age=$(($(date +%s) - $(stat -f %m "$HOME/.openclaw/.gateway.lock" 2>/dev/null || echo 0)))
        if [ $lock_age -gt 300 ]; then  # 5分钟前的锁文件
            rm -f "$HOME/.openclaw/.gateway.lock"
            cleaned=1
        fi
    fi
    
    if [ $cleaned -eq 1 ]; then
        log_message "🧹 清理了过期的锁文件"
    fi
}

# 主函数
main() {
    log_message "🔍 开始检查..."
    
    # 检查进程
    if ! check_gateway_process; then
        exit 1
    fi
    
    # 检查响应
    if ! check_gateway_response; then
        log_message "⚠️ Gateway 无响应，等待 30 秒后重试..."
        sleep 30
        if ! check_gateway_response; then
            log_message "🚨 Gateway 持续无响应，重启服务..."
            launchctl unload ~/Library/LaunchAgents/ai.openclaw.gateway.plist 2>/dev/null
            sleep 3
            launchctl load ~/Library/LaunchAgents/ai.openclaw.gateway.plist 2>/dev/null
            log_message "✅ 已重启 Gateway"
            exit 0
        fi
    fi
    
    # 检查卡住的任务
    check_stuck_tasks
    
    # 检查错误
    check_error_logs
    
    # 清理锁文件
    cleanup_locks
    
    log_message "✅ 检查完成，一切正常"
}

main
