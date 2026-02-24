# 桌面 AI POC - 小规模验证说明

## 目的

验证「AX 优先 + 视觉回退」方案是否可行，再做完整投入。

## 前置条件

1. **权限**：系统设置 → 隐私与安全性 → 辅助功能 → 允许终端/Python
2. **应用**：飞书 (Lark) 已安装
3. **依赖**：
   - `pyobjc-framework-ApplicationServices`（系统 Python 通常已有）
   - `peekaboo`（`brew install steipete/tap/peekaboo`）
   - **推荐** `cliclick`（`brew install cliclick`）— 点击更可靠

## 使用方法

> **注意**：需使用带 pyobjc 的 Python（如 `python3.9`）。若 `python3` 报错 `No module named 'ApplicationServices'`，请执行：
> `pip3 install pyobjc-framework-ApplicationServices` 或 `python3.9 poc_run.py --ax-only`

### 1. 仅测试 AX 树（不执行操作）

先确认 AX 能否抓取飞书界面：

```bash
cd /Users/oscar/moltbot
python3.9 poc_run.py --ax-only
# 或: python3 poc_run.py --ax-only  （若 pyobjc 已安装）
```

- 会抓取 AX 树并保存到 `/tmp/ax_tree_poc.json`
- 会列出包含「发送」的控件和输入框
- **不执行任何点击或输入**

### 2. 运行完整 POC

```bash
python3.9 poc_run.py --full
```

**操作前请**：
1. 打开飞书
2. 进入与「文件助手」的聊天界面
3. 输入框可见、可输入

**流程**：
1. 在输入框输入「POC测试」
2. 点击发送按钮

**结果**：会输出每步是 AX 成功、坐标点击成功，还是视觉回退成功。

## 人机配合学习（丰富信息）

当 AX 和视觉都找不到发送按钮时，会提示：
> 请将鼠标移动到【发送】上，然后按回车（我们将记住位置、模板、AX 路径供下次使用）

用户将鼠标移到发送按钮上并按回车后，会采集并保存：

| 类型 | 说明 | 抗窗口缩放/移动 |
|------|------|-----------------|
| **绝对坐标** | (x, y) | 否 |
| **相对位置** | 相对窗口/屏幕的比例 | 是 |
| **视觉模板** | 目标区域裁剪图（供 `cv2.matchTemplate`） | 部分 |
| **AX 路径** | 该坐标下的 AX 元素路径 | 是（若 AX 结构稳定） |
| **描述** | 供 vision AI 使用的文字 | - |

查找顺序：窗口相对 → 屏幕相对 → 模板匹配 → AX 路径 → 绝对坐标

**视觉成功时也会自动记住**：若视觉定位到发送按钮并点击成功，同样会保存上述信息供下次使用。

## 文件说明

| 文件 | 说明 |
|------|------|
| `ax_poc.py` | AX 语义树抓取、语义查询、AX 操作、`find_element_at_point` |
| `poc_run.py` | POC 主流程，AX 优先 + 视觉回退 + 人机学习 |
| `learned_positions.py` | 人机配合学习：丰富信息（模板、相对、AX 路径、描述） |
| `POC_README.md` | 本说明 |

模板匹配依赖 `opencv-python`（`pip install opencv-python`）。若未安装，将跳过模板策略，仍可用相对/AX/坐标。

## 成功标准

- [ ] AX 能抓取飞书 AX 树
- [ ] 能通过语义查询找到「发送」按钮和输入框
- [ ] AX 或坐标点击能执行操作
- [ ] AX 失败时视觉能兜底

## 已知限制（飞书）

飞书基于 Electron，AX 支持有限：
- 许多控件的 `title`、`frame` 为空
- 发送按钮可能无「发送」文字
- **重要**：AX 树中多个按钮无区分度，盲目取「最后一个」会点到错误按钮（如 Aa、表情），导致 AX 报告成功但实际未发送
- 当前策略：无语义匹配时**直接走视觉回退**，用视觉定位蓝色发送按钮

## 若失败

1. **AX 树抓不到**：检查辅助功能权限，确认飞书在前台
2. **找不到控件**：飞书可能用自定义控件，检查 `/tmp/ax_tree_poc.json` 看实际 role/title
3. **视觉回退失败**：确认 `PLATFORM302_API_KEY` 等环境变量，vision_agent 依赖正常
