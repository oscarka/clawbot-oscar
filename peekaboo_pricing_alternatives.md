# Peekaboo 定价与免费替代方案

## Peekaboo 定价情况

根据 OpenClaw 的集成情况：

### ✅ **Peekaboo CLI 本身是免费的**

- Peekaboo 通过 `brew install steipete/tap/peekaboo` 安装
- CLI 工具本身**不需要付费**
- `peekaboo capture live` 功能**免费使用**

### ⚠️ **但需要注意：**

1. **AI 分析功能需要付费**
   - `peekaboo see --analyze` 需要 OpenAI API Key
   - 使用 OpenAI 的视觉模型，会产生 API 费用
   - 但 `capture live` 本身（只录制，不分析）是免费的

2. **Peekaboo Bridge（可选）**
   - 如果需要更高级的功能，可能需要 Peekaboo Bridge
   - 但基础 CLI 功能已经足够

## 免费替代方案

### 方案 1: macOS 原生工具 ✅ **推荐**

**使用 `screencapture` + 定时截图**

```bash
# 定时截图（每 0.5 秒）
while true; do
    screencapture -x /tmp/screenshot_$(date +%s).png
    sleep 0.5
done
```

**优点：**
- ✅ 完全免费（macOS 内置）
- ✅ 无需安装
- ✅ 无 API 费用
- ✅ 可以配合 AI 分析（使用免费的 GLM-4.6v-flash）

**缺点：**
- ❌ 不如 Peekaboo 功能丰富
- ❌ 无法直接录制视频流

### 方案 2: FFmpeg（免费开源）✅

**实时屏幕录制**

```bash
# 安装 FFmpeg
brew install ffmpeg

# 录制屏幕（实时）
ffmpeg -f avfoundation -framerate 2 -i "1:0" -t 10 /tmp/capture.mp4

# 提取关键帧
ffmpeg -i /tmp/capture.mp4 -vf "fps=2" /tmp/frames/frame_%04d.png
```

**优点：**
- ✅ 完全免费开源
- ✅ 功能强大
- ✅ 可以录制视频并提取帧
- ✅ 支持多种格式

**缺点：**
- ❌ 需要安装
- ❌ 配置稍复杂

### 方案 3: Python + PIL（免费）✅

**定时截图 + AI 分析**

```python
from PIL import ImageGrab
import time

# 实时截图循环
while True:
    screenshot = ImageGrab.grab()
    screenshot.save(f"/tmp/screenshot_{int(time.time())}.png")
    # 发送给 AI 分析（使用免费的 GLM-4.6v-flash）
    time.sleep(0.5)
```

**优点：**
- ✅ 完全免费
- ✅ Python 库，易于集成
- ✅ 可以精确控制截图频率

**缺点：**
- ❌ 需要 Python 环境
- ❌ 性能可能不如原生工具

### 方案 4: PyAutoGUI（免费）✅

**屏幕自动化 + 截图**

```python
import pyautogui
import time

# 定时截图
while True:
    screenshot = pyautogui.screenshot()
    screenshot.save(f"/tmp/screenshot_{int(time.time())}.png")
    time.sleep(0.5)
```

**优点：**
- ✅ 完全免费
- ✅ 同时支持截图和自动化
- ✅ 跨平台

**缺点：**
- ❌ 需要 Python 环境
- ❌ macOS 上需要权限

## 推荐方案对比

| 方案 | 成本 | 安装难度 | 功能丰富度 | 推荐度 |
|------|------|----------|------------|--------|
| **Peekaboo CLI** | ✅ 免费 | ⭐⭐ 简单 | ⭐⭐⭐⭐⭐ 最丰富 | ⭐⭐⭐⭐⭐ |
| macOS screencapture | ✅ 免费 | ⭐ 无需安装 | ⭐⭐⭐ 基础 | ⭐⭐⭐⭐ |
| **FFmpeg** | ✅ 免费 | ⭐⭐ 简单 | ⭐⭐⭐⭐ 强大 | ⭐⭐⭐⭐ |
| Python + PIL | ✅ 免费 | ⭐⭐⭐ 中等 | ⭐⭐⭐ 基础 | ⭐⭐⭐ |
| PyAutoGUI | ✅ 免费 | ⭐⭐⭐ 中等 | ⭐⭐⭐⭐ 丰富 | ⭐⭐⭐ |

## 结论

### ✅ **Peekaboo capture live 本身是免费的！**

- CLI 工具免费
- `capture live` 功能免费
- 只需要 macOS 屏幕录制权限

### 💡 **如果不想用 Peekaboo，推荐：**

1. **macOS screencapture** - 最简单，无需安装
2. **FFmpeg** - 功能强大，可以录制视频
3. **Python + PIL** - 易于集成到现有代码

### ⚠️ **需要注意：**

- Peekaboo 的 **AI 分析功能**（`peekaboo see --analyze`）需要 OpenAI API，会产生费用
- 但我们可以用 **免费的 GLM-4.6v-flash** 替代 AI 分析
- `capture live` 只是录制，不涉及 AI，完全免费

## 实际使用建议

**当前最佳方案：**

```bash
# 使用 Peekaboo 免费功能录制
peekaboo capture live --mode screen --duration 10 --active-fps 2 --path /tmp/capture

# 使用免费的 GLM-4.6v-flash 分析（不花钱）
# 而不是 peekaboo see --analyze（需要 OpenAI API）
```

这样既享受 Peekaboo 的强大功能，又完全免费！
