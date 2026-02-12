#!/bin/bash

# 权限检查脚本 - 帮助诊断屏幕录制权限问题

echo "=========================================="
echo "权限诊断工具"
echo "=========================================="
echo ""

echo "1. 检查 Peekaboo 权限状态："
peekaboo permissions 2>&1
echo ""

echo "2. 当前终端信息："
echo "   进程名: $(ps -p $$ -o comm=)"
echo "   PID: $$"
echo "   路径: $(ps -p $$ -o command= | cut -d' ' -f1)"
echo ""

echo "3. 测试截图功能："
if peekaboo image --mode screen --path /tmp/permission_test.png 2>&1 | grep -q "Error"; then
    echo "   ❌ Peekaboo 截图失败"
    echo ""
    echo "4. 尝试使用 screencapture（macOS 原生）："
    if screencapture -x /tmp/permission_test2.png 2>&1; then
        if [ -f /tmp/permission_test2.png ]; then
            echo "   ✅ screencapture 可以工作"
            ls -lh /tmp/permission_test2.png
            rm /tmp/permission_test2.png
        else
            echo "   ❌ screencapture 也失败"
        fi
    else
        echo "   ❌ screencapture 失败"
    fi
else
    if [ -f /tmp/permission_test.png ]; then
        echo "   ✅ Peekaboo 截图成功！"
        ls -lh /tmp/permission_test.png
        rm /tmp/permission_test.png
    fi
fi
echo ""

echo "5. 系统设置检查建议："
echo "   请前往：系统设置 → 隐私与安全性 → 屏幕录制"
echo "   确保以下应用已勾选："
echo "   - Terminal（如果使用系统终端）"
echo "   - iTerm2（如果使用 iTerm2）"
echo "   - peekaboo（如果存在）"
echo "   - zsh（如果直接运行 zsh）"
echo ""

echo "6. 如果权限已添加但仍不工作，请尝试："
echo "   a) 完全退出终端（关闭所有窗口）"
echo "   b) 重新打开终端"
echo "   c) 或者重启电脑"
echo ""

echo "=========================================="
