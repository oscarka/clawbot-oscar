# Cursor IDE 监控和自动化方案

## 概述

这个方案允许 **moltbot** 监控 Cursor IDE 的聊天窗口，在检测到窗口停止更新或思路偏差时，通过 WhatsApp 通知你，并根据你的确认执行相应的 GUI 操作。

## 架构

```
┌─────────────────┐
│  Cursor IDE     │ ← 工作状态
│  (聊天窗口)     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 监控脚本         │ ← 每10秒检查一次
│ cursor_monitor.sh│
└────────┬────────┘
         │
         ├─→ 检测到停止/偏差
         │
         ▼
┌─────────────────┐
│ OpenClaw Gateway│ ← 发送 WhatsApp
│ (send method)   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  WhatsApp        │ ← 通知你
│  (+8613701223827)│
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  你的回复        │ ← 暂停/修改/继续
│  (通过 WhatsApp)│
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 自动化脚本       │ ← 执行操作
│ cursor_automation│
│ .sh              │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Peekaboo       │ ← GUI 自动化
│  (点击/输入)    │
└─────────────────┘
```

## 前置要求

### 1. 权限设置

#### 屏幕录制权限
1. 打开 **系统设置** → **隐私与安全性** → **屏幕录制**
2. 添加以下应用（根据你使用的终端）：
   - **Terminal** 或 **iTerm2** 或 **zsh**
   - **Peekaboo**（如果单独安装）

#### 辅助功能权限
1. 打开 **系统设置** → **隐私与安全性** → **辅助功能**
2. 确保以下应用已勾选：
   - **Terminal** 或 **iTerm2**
   - **Peekaboo**

### 2. 检查 Peekaboo

```bash
# 检查是否安装
which peekaboo

# 检查权限
peekaboo permissions

# 应该显示：
# Screen Recording (Required): Granted
# Accessibility (Required): Granted
```

### 3. 确认 WhatsApp 通道

```bash
cd /Users/oscar/moltbot/openclaw
pnpm openclaw gateway status
```

确保 Gateway 正常运行，WhatsApp 通道已登录。

## 使用方法

### 启动监控

```bash
# 基本使用（默认10秒间隔）
bash /Users/oscar/moltbot/cursor_monitor.sh

# 自定义间隔（5秒）
bash /Users/oscar/moltbot/cursor_monitor.sh --interval 5

# 自定义 WhatsApp 目标
bash /Users/oscar/moltbot/cursor_monitor.sh --whatsapp +8613701223827
```

### 后台运行

```bash
# 使用 nohup
nohup bash /Users/oscar/moltbot/cursor_monitor.sh > /dev/null 2>&1 &

# 或使用 screen/tmux
screen -S cursor_monitor
bash /Users/oscar/moltbot/cursor_monitor.sh
# Ctrl+A, D 退出 screen
```

### 查看日志

```bash
tail -f ~/.openclaw/cursor_monitor.log
```

## 自动化操作

当收到 WhatsApp 通知后，你可以通过以下方式操作：

### 方式 1：直接运行脚本

```bash
# 暂停对话
bash /Users/oscar/moltbot/cursor_automation.sh pause

# 修改对话方向
bash /Users/oscar/moltbot/cursor_automation.sh modify "请改用更简单的方法"

# 继续对话
bash /Users/oscar/moltbot/cursor_automation.sh continue

# 输入自定义文本
bash /Users/oscar/moltbot/cursor_automation.sh type "你好，请继续"
```

### 方式 2：通过 OpenClaw Agent（推荐）

更好的方案是通过 OpenClaw Agent 监听 WhatsApp 消息，自动解析你的回复并执行操作。

#### 创建 OpenClaw Skill

在 OpenClaw 的 workspace 中创建一个 skill，监听 WhatsApp 消息中的特定命令：

```bash
# 在 WhatsApp 中发送：
# /cursor pause      - 暂停
# /cursor modify 请改用更简单的方法  - 修改
# /cursor continue   - 继续
```

## 工作流程示例

### 场景 1：检测到窗口停止

1. **监控脚本检测**：Cursor 聊天窗口超过 30 秒没有更新
2. **分析截图**：使用 Peekaboo 的 `--analyze` 功能分析当前对话状态
3. **发送通知**：通过 WhatsApp 发送：
   ```
   🤖 Cursor 监控通知
   
   检测到 Cursor IDE 聊天窗口已停止更新超过 30 秒。
   
   分析结果：
   [AI 分析的内容]
   
   请选择操作：
   1. 暂停 - 停止当前任务
   2. 修改 - 我来调整对话方向
   3. 继续 - 忽略此通知
   ```
4. **等待确认**：脚本等待你的 WhatsApp 回复
5. **执行操作**：根据你的回复执行相应操作

### 场景 2：检测到思路偏差

1. **监控脚本检测**：通过 AI 分析检测到对话方向可能有问题
2. **发送通知**：发送包含偏差分析的 WhatsApp 消息
3. **等待确认**：等待你的指示
4. **执行修改**：根据你的指示输入新的指令

## 配置选项

### 环境变量

```bash
# 监控间隔（秒）
export CURSOR_MONITOR_INTERVAL=10

# WhatsApp 目标
export CURSOR_MONITOR_WHATSAPP="+8613701223827"

# 运行监控
bash /Users/oscar/moltbot/cursor_monitor.sh
```

### 脚本参数

```bash
cursor_monitor.sh [--interval <秒>] [--whatsapp <号码>]
```

## 故障排除

### 问题 1：权限错误

**错误**：`"osascript"不允许辅助访问`

**解决**：
1. 系统设置 → 隐私与安全性 → 辅助功能
2. 添加 Terminal/iTerm2

### 问题 2：截图失败

**错误**：`截图失败`

**解决**：
1. 检查屏幕录制权限
2. 确保 Cursor 正在运行
3. 检查 Peekaboo 权限：`peekaboo permissions`

### 问题 3：WhatsApp 发送失败

**错误**：`发送失败`

**解决**：
1. 检查 Gateway 是否运行：`pnpm openclaw gateway status`
2. 检查 WhatsApp 通道是否登录
3. 检查 Gateway token 是否正确

### 问题 4：无法找到 Cursor 窗口

**错误**：`Cursor 未运行`

**解决**：
1. 确保 Cursor 应用正在运行
2. 检查应用名称是否正确（可能是 "Cursor" 或其他）

## 高级功能

### 自定义检测逻辑

编辑 `cursor_monitor.sh`，修改 `detect_stopped_window()` 函数，添加更智能的检测逻辑。

### 集成到 OpenClaw Agent

创建一个 OpenClaw Agent，监听 WhatsApp 消息，自动解析命令并调用 `cursor_automation.sh`。

### 添加更多自动化操作

在 `cursor_automation.sh` 中添加更多操作，如：
- 滚动聊天历史
- 切换对话
- 复制代码
- 等等

## 注意事项

1. **隐私**：监控脚本会截取屏幕内容，请确保在安全的环境中使用
2. **性能**：监控间隔不要设置太短（建议 ≥ 5 秒）
3. **权限**：需要授予必要的系统权限
4. **测试**：先在测试环境中验证功能

## 下一步

1. ✅ 授予屏幕录制权限
2. ✅ 测试监控脚本
3. ✅ 测试自动化操作
4. ⏳ 集成到 OpenClaw Agent（可选）
5. ⏳ 优化检测逻辑
