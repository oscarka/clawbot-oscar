# Cursor 监控权限问题解决方案

## 问题

即使已经在系统设置中添加了 Terminal 的屏幕录制权限，Peekaboo 仍然无法截图。

## 可能的原因

1. **需要重启终端**：添加权限后，需要重启终端才能生效
2. **Peekaboo 需要特定权限**：Peekaboo 可能需要通过应用本身获取权限，而不是通过终端
3. **权限缓存问题**：macOS 的权限系统可能需要刷新

## 解决方案

### 方案 1：重启终端（最简单）

1. **完全退出当前终端**
   - 关闭所有终端窗口
   - 或者使用 `killall Terminal` 或 `killall iTerm2`

2. **重新打开终端**

3. **再次运行脚本**
   ```bash
   bash /Users/oscar/moltbot/cursor_monitor.sh --interval 5
   ```

### 方案 2：通过 Peekaboo.app 获取权限

1. **安装 Peekaboo.app**（如果还没有）
   ```bash
   brew install --cask peekaboo
   ```

2. **打开 Peekaboo.app**
   - 首次打开时会请求屏幕录制权限
   - 授予权限

3. **运行脚本**
   - Peekaboo CLI 会通过 Peekaboo.app 获取权限

### 方案 3：使用 macOS 原生截图（已集成到脚本）

脚本已经更新，如果 Peekaboo 失败，会自动尝试使用 macOS 原生的 `screencapture` 命令。

**注意**：`screencapture` 只能截取整个屏幕，无法精确定位到 Cursor 窗口。

### 方案 4：手动测试权限

```bash
# 测试 Peekaboo 权限
peekaboo permissions

# 测试实际截图
peekaboo image --mode screen --path /tmp/test.png

# 如果失败，尝试使用 screencapture
screencapture /tmp/test.png
```

## 推荐的解决步骤

1. **首先尝试重启终端**
   ```bash
   # 退出终端，重新打开，然后运行
   bash /Users/oscar/moltbot/cursor_monitor.sh --interval 5
   ```

2. **如果仍然失败，检查系统设置**
   - 系统设置 → 隐私与安全性 → 屏幕录制
   - 确认 Terminal（或你使用的终端）已勾选
   - 尝试取消勾选后重新勾选

3. **如果还是不行，安装 Peekaboo.app**
   ```bash
   brew install --cask peekaboo
   open -a Peekaboo
   # 授予权限后，再次运行脚本
   ```

## 验证权限是否生效

运行以下命令验证：

```bash
# 方法 1：检查权限状态
peekaboo permissions

# 方法 2：实际测试截图
peekaboo image --mode screen --path /tmp/test.png && echo "✅ 成功" || echo "❌ 失败"

# 方法 3：使用 screencapture（不需要特殊权限）
screencapture /tmp/test2.png && echo "✅ 成功" || echo "❌ 失败"
```

## 临时解决方案

如果权限问题无法解决，脚本已经更新为：
- 优先使用 Peekaboo（更精确）
- 如果 Peekaboo 失败，自动降级使用 `screencapture`（功能受限，但可以工作）

使用 `screencapture` 的限制：
- 只能截取整个屏幕
- 无法精确定位到 Cursor 窗口
- 无法使用 Peekaboo 的 UI 元素识别功能

## 下一步

1. 重启终端并测试
2. 如果问题仍然存在，告诉我具体的错误信息
3. 我们可以进一步调整脚本或寻找替代方案
