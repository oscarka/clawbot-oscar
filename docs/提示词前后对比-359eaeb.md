# System Prompt 前后对比（359eaeb 改动）

> 对比基准：`359eaeb^`（改动前） vs `359eaeb`（当前）

---

## 一、整体数据

| 指标 | 改动前 | 改动后 | 变化 |
|------|--------|--------|------|
| 行数 | 623 | 728 | **+105 行** |
| 字符数 | 29,057 | 39,716 | **+10,659 字符（+37%）** |
| 估算 token* | ~7,300 | ~9,900 | **+~2,600 token** |

\* 按混合中英文约 4 字符/token 估算

---

## 二、改动点逐项对比

### 2.1 message tool 说明（小改动）

**改动前**（约第 89 行）：
```
- For `action=send`, include `to` and `message`.
```

**改动后**：
```
- For `action=send`, you MUST always include `to` (the recipient channel/user ID) and `message`. Never omit `to` — it will fail with 'requires a target' if missing.
```

**说明**：强化了 `to` 必填，避免 Feishu 等渠道报错。约 +50 字符。

---

### 2.2 小红书 (XHS) 发布说明（大幅扩充）

**改动前**（约 6 行）：
```
### 小红书 (Xiaohongshu) 发布 — 必须用 exec + mcporter，禁止 local_vision / browser / 扩展
When the user asks to publish/post to 小红书...
- Run: `exec` with command `MCPORTER_CALL_TIMEOUT=300000 mcporter call xhs-toolkit.smart_publish_note --args '{\"title\":\"...\",\"content\":\"...\",\"images\":[...],\"topics\":[]}'`
- The MCPORTER_CALL_TIMEOUT=300000 prefix is REQUIRED...
- For login: ...
- For saving as draft...
**Image handling from Feishu**: ...
CRITICAL: Use **mcporter** CLI only. Never run `openclaw` for 小红书.
```

**改动后**（约 20 行）：
- 新增 **Python json.dumps 强制流程**：Step 1 用 Python heredoc 写 JSON 到文件，Step 2 用 `cat` 读文件调用 mcporter
- 新增 **HARD STOP**：禁止用 local_vision/browser 做小红书任务
- 原有内容保留并略微调整

**说明**：解决中文/emoji 手写 JSON 易出错的问题，但显著增加 prompt 长度。约 +600 字符。

---

### 2.3 新增：飞书文件及附加媒体处理（全新块）

**改动前**：无此块。

**改动后**（约 4 行）：
```
### 飞书(Feishu)文件及附加媒体处理
When a user says 'process these files' or replies to a message with a file, OpenClaw automatically extracts the file paths...
If you need to pass files to tools (like NotebookLM), ALWAYS check the provided `MediaPaths` list...
- For example, files sent in Feishu are saved locally to `/tmp/openclaw-cli-images-XXXXX/`...
```

**说明**：指导 agent 正确使用 Feishu 传来的文件路径。约 +350 字符。

---

### 2.4 核心变化：按 toolNames 分支（有 exec vs 无 exec）

**改动前**：所有 agent 共用同一套说明，没有按 `toolNames` 分支。小红书之后直接接「CRITICAL: Never say you can't use an app」。

**改动后**：引入 `params.toolNames?.includes("exec") ? [块A] : [块B]`：

#### 块 A：有 exec 的 agent（main 等）— 约 55 行

新增内容依次为：

1. **NotebookLM 全功能操作**（~35 行）
   - 生成 PPT / Slide Deck 的完整流程（Step 1 上传、Step 2 生成、轮询、发文件）
   - 生成 Infographic 的用法
   - 完整工作流：收集信息 → NotebookLM 概览图 → 发小红书
   - 其他操作：notebooks、ask、sources、podcast、upload 等

2. **Android 手机控制**（~6 行）
   - mcporter android-automation 的用法
   - 常用 App 的 package name

**估算**：约 +3,500 字符。

#### 块 B：无 exec 的 agent（fast）— 约 20 行

```
### ⚠️ CRITICAL: You MUST Call sessions_spawn Tool — Text Alone Is USELESS ⚠️

You are the FAST agent. For NotebookLM, Intel Search, or research tasks, you MUST call the `sessions_spawn` tool to assign the job to the `researcher` agent.

**Tool-calling rule**: You must OUTPUT A TOOL CALL, not just describe the action in text. Writing '已派给 @researcher' or '已指派' in your response WITHOUT actually calling the tool does NOTHING — the subagent will never run.

**WRONG (无效，subagent 不会运行):**
- Replying with text only: "📋 已派给 @researcher 处理：xxx"
- Replying with text only: "我已指派 researcher 去查了"
- Any response that does NOT include a tool_call for sessions_spawn

**RIGHT (正确):**
- FIRST: Call the `sessions_spawn` tool with agentId=researcher, task="<user request>"
- The tool returns status:accepted → THEN you may optionally say '已派给 @researcher'
- Your response MUST contain a tool_call block for sessions_spawn

**Trigger phrases**: NotebookLM, Intel Search, 查一下, 研究, 搜集信息, 伊朗/新闻 等 → immediately call sessions_spawn.

**Example**: User says '用 Intel Search 查伊朗最新信息' → You MUST output a tool_call: sessions_spawn(agentId=researcher, task="用 Intel Search 查伊朗24小时最新信息"). Do NOT output text-only.
```

**说明**：强制 fast agent 用 `sessions_spawn` 派活，禁止纯文字「已派给」。约 +900 字符。

---

## 三、按 agent 类型看 token 增量

| Agent 类型 | 条件 | 新增内容 | 估算新增 token |
|------------|------|----------|----------------|
| **main（有 exec）** | `toolNames` 含 `exec` | 小红书扩充 + 飞书文件 + NotebookLM 全块 + Android | **~2,400** |
| **fast（无 exec）** | `toolNames` 不含 `exec` | 飞书文件 + sessions_spawn 块 | **~320** |

---

## 四、结构对比示意

```
改动前（所有 agent 共用）:
├── ... 前面通用内容 ...
├── 小红书（~6 行，简短）
├── CRITICAL: Never say you can't use an app
└── ... 后面通用内容 ...

改动后（按 toolNames 分支）:
├── ... 前面通用内容 ...
├── 小红书（~20 行，含 Python JSON 流程）
├── 飞书文件及附加媒体处理（新增）
├── toolNames.includes("exec") ?
│   ├── [是] NotebookLM 全功能 + Android（~55 行）
│   └── [否] sessions_spawn 强制块（~20 行）
├── CRITICAL: Never say you can't use an app
└── ... 后面通用内容 ...
```

---

## 五、小结

| 项目 | 说明 |
|------|------|
| **总增量** | +105 行，+10,659 字符，约 +2,600 token |
| **main agent** | 每次请求多 ~2,400 token（NotebookLM + Android + 小红书扩充 + 飞书文件） |
| **fast agent** | 每次请求多 ~320 token（sessions_spawn 块 + 飞书文件） |
| **影响** | 所有请求都变长，main 更明显，导致首 token 延迟上升 |
