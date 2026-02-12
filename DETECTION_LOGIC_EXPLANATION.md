# Cursor 监控检测逻辑说明

## 当前实现的问题

### 原始检测方法（有问题）
```bash
# 比较文件路径是否相同
if [[ "$current_screenshot" == "$last_screenshot" ]]; then
    # 检查文件修改时间...
fi
```

**问题：**
- 每次截图都会生成新文件（带时间戳），路径永远不会相同
- 只检查文件路径，不检查实际内容
- 无法检测窗口内容是否真的停止更新

## 改进后的检测方法

### 方法 1：图片哈希比较（已实现）✅
```bash
# 计算图片的 MD5 哈希值
current_hash=$(md5 -q "$current_screenshot")
last_hash=$(cat "$last_state_file")

# 如果哈希值相同，说明内容没变
if [[ "$current_hash" == "$last_hash" ]]; then
    # 检查停止时间是否超过阈值
fi
```

**优点：**
- 快速、准确
- 能检测内容是否真的变化
- 不依赖文件路径

**缺点：**
- 只能检测完全相同的图片
- 如果窗口有微小变化（如光标闪烁），会误判

### 方法 2：OCR 文本提取比较（可选）
```bash
# 使用 OCR 提取窗口中的文本
current_text=$(tesseract "$current_screenshot" stdout 2>/dev/null)
last_text=$(cat "$last_text_file")

# 比较文本内容
if [[ "$current_text" == "$last_text" ]]; then
    # 内容未变化
fi
```

**优点：**
- 更关注实际内容（文本）
- 忽略视觉上的微小变化

**缺点：**
- 需要安装 Tesseract OCR
- 速度较慢
- 可能提取不准确

### 方法 3：AI 模型分析（已部分实现）✅
```bash
# 使用 Peekaboo 的 AI 分析功能
analysis=$(peekaboo see --path "$screenshot" --analyze "分析窗口状态...")
```

**优点：**
- 最智能，能理解上下文
- 可以检测"思路偏差"
- 能理解对话内容

**缺点：**
- 成本高（每次分析都要调用 AI）
- 速度慢
- 当前只在检测到停止后才使用

### 方法 4：进程状态检查（可选）
```bash
# 检查 Cursor 进程的 CPU 使用率
cpu_usage=$(ps aux | grep "[C]ursor.app" | awk '{print $3}')
if [[ $(echo "$cpu_usage < 1.0" | bc) -eq 1 ]]; then
    # CPU 使用率很低，可能停止工作
fi
```

**优点：**
- 能检测进程是否真的在工作
- 不依赖截图

**缺点：**
- 无法检测"思路偏差"
- 无法知道具体在做什么

## 当前实现（改进后）

### 检测流程
1. **截图** → 每 10 秒截取 Cursor 窗口
2. **哈希比较** → 计算当前截图的 MD5，与上次比较
3. **时间判断** → 如果内容 30 秒未变化，认为停止
4. **AI 分析** → 检测到停止后，使用 AI 分析具体原因
5. **通知用户** → 通过 WhatsApp 发送通知

### 检测逻辑
```bash
# 1. 计算当前截图哈希
current_hash=$(md5 -q "$screenshot")

# 2. 与上次比较
if [[ "$current_hash" == "$last_hash" ]]; then
    # 3. 检查停止时间
    if [[ $time_since_change -gt 30 ]]; then
        # 4. 触发 AI 分析
        analysis=$(analyze_screenshot "$screenshot" "分析窗口状态...")
        # 5. 发送通知
        send_whatsapp_notification "$analysis"
    fi
fi
```

## 未来改进方向

### 1. 混合检测策略
- 先用哈希快速检测（低成本）
- 检测到可能停止后，再用 AI 深度分析（高成本但准确）

### 2. 文本变化检测
- 提取聊天窗口的文本内容
- 比较文本是否变化
- 更关注实际对话内容

### 3. 智能阈值
- 根据 Cursor 的工作模式调整检测间隔
- 代码生成时：检测间隔短（5秒）
- 思考时：检测间隔长（30秒）

### 4. 上下文理解
- 使用 AI 理解对话上下文
- 检测"思路偏差"（如偏离主题、重复错误）
- 不只是检测"停止"，还要检测"偏差"

## 总结

**当前实现：**
- ✅ 使用图片哈希比较（快速、准确）
- ✅ 结合时间阈值判断（30秒）
- ✅ 检测到停止后使用 AI 分析（智能）

**不是通过：**
- ❌ 进程状态（无法知道具体在做什么）
- ❌ 文件路径（每次都是新文件）

**是通过：**
- ✅ 图片内容哈希（检测内容是否变化）
- ✅ AI 模型分析（理解上下文和状态）
