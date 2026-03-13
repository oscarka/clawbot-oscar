# 代码技能归纳与新 Agent 规划

> 不动代码，仅规划。把代码相关技能归纳到一个新 agent。**用途+举例说清楚，你来判断归属。**

---

## 一、明确排除：不是 coder 的活

| 场景 | 举例 | 应归谁 |
|------|------|--------|
| **运营类** | 小红书发布、抖音发视频、公众号排版 | main 或专门的运营 agent |
| **通过 MCP 做运营** | 用 MCP 控制手机发小红书、批量发帖 | main / 运营 agent，**不是 coder** |
| **找技能、装技能** | 「帮我找个 React 技能」「装 gcp-cloud-run 到 main」 | skill-procurement |

coder 的边界：**写代码、改代码、跑代码、开发协作、调试**。运营、发帖、内容生产不归 coder。

---

## 二、技能清单：用途 + 举例，供你判断

每个技能下面写清：**用途**、**典型举例**、**可能归属**。你来勾选哪些给 coder。

---

### 2.1 coding-agent

**用途**：通过 bash 后台运行 Codex、Claude Code、OpenCode、Pi 等编码 agent，做程序化控制。

**举例**：
- 「用 Codex 帮我重构这个文件」
- 「让 Pi 写个脚本自动部署」
- 「在 tmux 里跑 OpenCode，我稍后接过去」

**可能归属**：coder（纯开发工具）

---

### 2.2 github

**用途**：gh CLI 操作 GitHub：issues、PR、CI runs、API 查询。

**举例**：
- 「看看 PR #55 的 CI 挂了没」
- 「开个 issue 记录这个 bug」
- 「用 gh api 查一下最近 10 个 PR 的 review 状态」

**可能归属**：coder（代码协作）

---

### 2.3 tmux

**用途**：远程控制 tmux 会话，发送按键、抓取 pane 输出，适合交互式 CLI。

**举例**：
- 「在 tmux 里起个 Python REPL，我待会要接」
- 「把那个跑着的 node 进程的输出抓给我看看」
- 「给 tmux 会话发个 Ctrl+C 停掉」

**可能归属**：coder（开发/调试时的终端管理）

---

### 2.4 session-logs

**用途**：用 jq 搜索、分析历史会话 JSONL 日志。

**举例**：
- 「上次对话里我说了什么？」
- 「查一下上周 main 会话里有没有提到这个 API」
- 「分析一下那次失败的任务，tool call 顺序是什么」

**可能归属**：coder（调试、复盘）或 main（通用复盘）

---

### 2.5 model-usage

**用途**：CodexBar CLI 查看 Codex/Claude 的模型用量和成本。

**举例**：
- 「这个月 Codex 花了多少钱」
- 「按模型 breakdown 一下用量」

**可能归属**：coder（开发者关心成本）或 main（个人助理关心账单）

---

### 2.6 skill-creator

**用途**：设计、结构化、打包 AgentSkills：写 SKILL.md、组织脚本和资源、定义触发条件。

**举例**：
- 「帮我写一个 skill，教 agent 怎么用 xxx CLI」
- 「把这个工作流打包成 skill，以后可以复用」
- 「设计一个 skill 的结构，包含安装说明和示例」

**可能归属**：**存疑**。偏「技能设计/元工作」，可能归 skill-procurement 延伸，也可能归 coder（写文档+脚本）。你来定。

---

### 2.7 clawdhub

**用途**：搜索、安装、更新、发布 agent skills（ClawdHub 生态）。

**举例**：
- 「clawdhub search react」
- 「clawdhub install xxx --workdir ~/.openclaw/workspace-main」
- 「把这个 skill 发布到 clawdhub」

**可能归属**：**skill-procurement**（找+装是它的活）。coder 一般不需要，除非「我开发了一个 skill 要发布」——那发布可以算 coder，但搜索安装应归 skill-procurement。

---

### 2.8 oracle

**用途**：用 oracle CLI 把 prompt + 选中的文件打包成一次请求，发给另一模型（如 ChatGPT）做带上下文的问答。

**举例**：
- 「把这个 bug 的堆栈和相关代码打包发给 GPT 分析」
- 「把这段复杂逻辑打包给 Claude 看，让它给建议」

**可能归属**：coder（调试、复杂问题求外援）或 main（通用「让另一个模型帮我看」）

---

### 2.9 mcporter

**用途**：管理、调用 MCP 服务器/工具，HTTP 或 stdio。**通用工具**，谁用取决于调什么 MCP。

**举例（coder 可能用）**：
- 「用 mcporter 调 Linear 查 issues」
- 「调一个代码分析 MCP 做静态检查」

**举例（非 coder）**：
- 「用 MCP 控制手机发小红书」→ 运营，归 main/运营 agent
- 「用 android-automation MCP 点一下」→ 可能是测试，也可能是运营

**可能归属**：**不专属 coder**。mcporter 是通道，不同 agent 调不同 MCP。coder 若只调开发类 MCP，可放 coder；若 main 也要调运营类 MCP，mcporter 可共享。

---

### 2.10 find-skills

**用途**：npx skills find，搜索 npm 生态的 agent skills。

**举例**：
- 「skills find react testing」
- 「找找有没有 PR review 相关的 skill」

**可能归属**：**skill-procurement**（找技能是它的核心职责）

---

### 2.11 android-automation

**用途**：通过 MCP 控制 Android：点击、滑动、输入、截图、UI 层级。

**举例**：
- 「帮我点一下登录按钮」（可能是测试）
- 「截图当前屏幕」（可能是调试）
- 「发小红书」→ 运营，不归 coder

**可能归属**：**不归 coder**。开发/测试场景少，运营场景多；若归，更可能是 main 或运营 agent。

---

## 三、建议归属汇总（供你勾选）

| 技能 | 建议归属 | 理由 |
|------|----------|------|
| coding-agent | coder | 纯开发 |
| github | coder | 代码协作 |
| tmux | coder | 开发终端 |
| session-logs | coder 或 main | 调试/复盘 |
| model-usage | coder 或 main | 用量/成本 |
| skill-creator | **你来定** | 偏元工作，可能 skill-procurement 或 coder |
| clawdhub | skill-procurement | 找+装技能 |
| oracle | coder 或 main | 调试求外援 |
| mcporter | **共享** 或按 MCP 类型分 | 通用通道，运营类不归 coder |
| find-skills | skill-procurement | 找技能 |
| android-automation | main / 运营 | 小红书等运营不归 coder |

---

## 四、新 Agent 定位（待你定稿后）

**名称建议**：`coder` 或 `dev`

**职责（按你勾选结果）**：
- 写代码、改代码、跑代码
- GitHub 协作（PR、CI、issues）
- 开发终端管理（tmux）
- 调试、复盘（session-logs）
- （若归 coder）skill-creator、oracle、model-usage 等

---

## 五、实施步骤（不改代码的规划）

### 3.1 创建 workspace

```bash
mkdir -p ~/.openclaw/workspace-coder
```

### 3.2 复制 bootstrap 文件

```bash
cp ~/.openclaw/workspace/AGENTS.md ~/.openclaw/workspace-coder/
cp ~/.openclaw/workspace/SOUL.md ~/.openclaw/workspace-coder/
cp ~/.openclaw/workspace/USER.md ~/.openclaw/workspace-coder/
cp ~/.openclaw/workspace/TOOLS.md ~/.openclaw/workspace-coder/
# 如有 memory 目录
cp -r ~/.openclaw/workspace/memory ~/.openclaw/workspace-coder/ 2>/dev/null || true
```

### 3.3 创建 coder 专属 AGENTS.md

在 `~/.openclaw/workspace-coder/AGENTS.md` 中写明：
- 身份：代码/开发专用 agent
- 必读：SOUL.md、USER.md、memory
- 核心技能列表：**按你勾选结果填写**（建议至少：coding-agent、github、tmux）
- 安全规则：不随意执行破坏性命令、不泄露密钥

### 3.4 创建 skills 目录并链接/复制技能

**按你最终确定的归属**，只把归 coder 的技能放进 `workspace-coder/skills/`。

示例（若你确定 coder 要：coding-agent、github、tmux、session-logs、model-usage）：

```bash
mkdir -p ~/.openclaw/workspace-coder/skills
cd ~/.openclaw/workspace-coder/skills
ln -s /path/to/openclaw/skills/coding-agent .
ln -s /path/to/openclaw/skills/github .
ln -s /path/to/openclaw/skills/tmux .
ln -s /path/to/openclaw/skills/session-logs .
ln -s /path/to/openclaw/skills/model-usage .
# skill-creator、oracle、mcporter 等按你勾选结果决定是否加
```

### 3.5 修改 openclaw.json 配置

在 `~/.openclaw/openclaw.json` 的 `agents.list` 中新增：

```json5
{
  agents: {
    list: [
      // ... 现有 main, fast, researcher, skill-procurement
      {
        id: "coder",
        name: "Coder",
        workspace: "~/.openclaw/workspace-coder"
        // model、sandbox 等按需配置
      }
    ]
  }
}
```

### 3.6 配置 bindings（可选）

若希望某些渠道/对话自动路由到 coder，在 `bindings` 中增加匹配规则，例如：
- 某 Discord channel → coder
- 某 WhatsApp 账号的「代码」关键词 → coder
- 或通过 Fast 派活：`sessions_spawn(agentId: "coder", task: "...")`

---

## 六、技能依赖检查（按你勾选的技能）

| 技能 | 需安装的二进制 |
|------|----------------|
| coding-agent | claude / codex / opencode / pi（任一） |
| github | gh |
| tmux | tmux |
| session-logs | jq, rg |
| model-usage | codexbar |
| skill-creator | 无 |
| clawdhub | clawdhub |
| oracle | oracle |
| mcporter | mcporter |

只给 coder 装你勾选的那些技能；缺失的二进制在首次使用时提示用户安装。

---

## 七、边界速查（按你最终归属调整）

| 场景 | 负责 agent |
|------|------------|
| 找/装技能（clawdhub、find-skills） | skill-procurement |
| 写 PR、跑 CI、查 issues | coder |
| 用 Codex/Pi 写代码 | coder |
| 分析上次会话为什么失败 | coder（若有 session-logs）或 main |
| 创建一个新 skill（skill-creator） | **你来定**：coder 或 skill-procurement 延伸 |
| 用 MCP 发小红书、运营发帖 | main / 运营 agent，**不是 coder** |
| 用 gcp-cloud-run 部署 | main 或 coder（若 coder 有部署类技能） |

skill-procurement 专注「找+装」，coder 专注「用+写」，运营类不归 coder。

---

## 八、总结

| 步骤 | 操作 |
|------|------|
| 1 | 你勾选完归属后，创建 `~/.openclaw/workspace-coder` |
| 2 | 复制 AGENTS.md、SOUL.md、USER.md、TOOLS.md |
| 3 | 编写 coder 专属 AGENTS.md（身份 + 你勾选的技能列表） |
| 4 | 在 `workspace-coder/skills/` 下只链接/复制**归 coder** 的技能 |
| 5 | 在 openclaw.json 的 `agents.list` 中新增 coder |
| 6 | 按需配置 bindings 或通过 Fast 派活 |

**不动代码**：以上均为配置与文件操作，无需改 openclaw 源码。
