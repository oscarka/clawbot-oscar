#!/bin/bash

# OpenClaw 自动清理脚本
# 使用方法：添加到 crontab，每天凌晨 3 点执行
# 0 3 * * * /Users/oscar/moltbot/openclaw_auto_cleanup.sh >> ~/.openclaw/cleanup.log 2>&1

LOG_FILE="$HOME/.openclaw/cleanup.log"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

# 配置
MAX_SESSION_SIZE_MB=10      # 会话文件最大 10MB
MAX_LOG_SIZE_MB=100         # 日志文件最大 100MB
KEEP_SESSION_DAYS=7         # 保留最近 7 天的会话
KEEP_LOG_DAYS=30            # 保留最近 30 天的日志

log_message() {
    echo "[$TIMESTAMP] $1" >> "$LOG_FILE"
}

# 清理过大的会话文件
cleanup_large_sessions() {
    local cleaned=0
    local sessions_dir="$HOME/.openclaw/agents/main/sessions"
    
    if [ -d "$sessions_dir" ]; then
        while IFS= read -r file; do
            if [ -n "$file" ]; then
                local size_mb=$(du -m "$file" | cut -f1)
                if [ $size_mb -gt $MAX_SESSION_SIZE_MB ]; then
                    log_message "🧹 清理过大会话文件: $(basename $file) (${size_mb}MB)"
                    # 备份后删除
                    mv "$file" "${file}.backup.$(date +%Y%m%d)" 2>/dev/null
                    cleaned=$((cleaned + 1))
                fi
            fi
        done < <(find "$sessions_dir" -name "*.jsonl" -type f 2>/dev/null)
    fi
    
    if [ $cleaned -gt 0 ]; then
        log_message "✅ 清理了 $cleaned 个过大的会话文件"
    fi
}

# 清理旧的会话文件
cleanup_old_sessions() {
    local sessions_dir="$HOME/.openclaw/agents/main/sessions"
    local cleaned=0
    
    if [ -d "$sessions_dir" ]; then
        cleaned=$(find "$sessions_dir" -name "*.jsonl" -type f -mtime +$KEEP_SESSION_DAYS -delete -print | wc -l | tr -d ' ')
    fi
    
    if [ $cleaned -gt 0 ]; then
        log_message "✅ 清理了 $cleaned 个旧会话文件（超过 ${KEEP_SESSION_DAYS} 天）"
    fi
}

# 压缩过大的日志文件
compress_large_logs() {
    local logs_dir="$HOME/.openclaw/logs"
    local compressed=0
    
    if [ -d "$logs_dir" ]; then
        while IFS= read -r file; do
            if [ -n "$file" ] && [ ! -f "${file}.gz" ]; then
                local size_mb=$(du -m "$file" | cut -f1)
                if [ $size_mb -gt $MAX_LOG_SIZE_MB ]; then
                    log_message "📦 压缩大日志文件: $(basename $file) (${size_mb}MB)"
                    gzip "$file" 2>/dev/null
                    compressed=$((compressed + 1))
                fi
            fi
        done < <(find "$logs_dir" -name "*.log" -type f 2>/dev/null)
    fi
    
    if [ $compressed -gt 0 ]; then
        log_message "✅ 压缩了 $compressed 个日志文件"
    fi
}

# 清理旧的日志文件
cleanup_old_logs() {
    local logs_dir="$HOME/.openclaw/logs"
    local cleaned=0
    
    if [ -d "$logs_dir" ]; then
        cleaned=$(find "$logs_dir" -name "*.log.gz" -type f -mtime +$KEEP_LOG_DAYS -delete -print | wc -l | tr -d ' ')
    fi
    
    if [ $cleaned -gt 0 ]; then
        log_message "✅ 清理了 $cleaned 个旧日志文件（超过 ${KEEP_LOG_DAYS} 天）"
    fi
}

# 清理临时文件
cleanup_temp_files() {
    local cleaned=0
    
    # 清理锁文件
    if [ -f "$HOME/.openclaw/.gateway.lock" ]; then
        local lock_age=$(($(date +%s) - $(stat -f %m "$HOME/.openclaw/.gateway.lock" 2>/dev/null || echo 0)))
        if [ $lock_age -gt 3600 ]; then  # 1小时前的锁文件
            rm -f "$HOME/.openclaw/.gateway.lock"
            cleaned=$((cleaned + 1))
        fi
    fi
    
    # 清理临时锁文件
    local temp_locks=$(find /tmp -name "openclaw-*.lock" -type f -mtime +1 -delete -print | wc -l | tr -d ' ')
    cleaned=$((cleaned + temp_locks))
    
    if [ $cleaned -gt 0 ]; then
        log_message "✅ 清理了 $cleaned 个临时锁文件"
    fi
}

# 主函数
main() {
    log_message "🧹 开始自动清理..."
    
    cleanup_large_sessions
    cleanup_old_sessions
    compress_large_logs
    cleanup_old_logs
    cleanup_temp_files
    
    log_message "✅ 清理完成"
}

main
