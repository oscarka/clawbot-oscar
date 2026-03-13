# Fast 派给 researcher 而非 skill-procurement 的根因分析

## 现象

用户请求：「用网络搜索查找目前最热门的 OpenClaw/AI Agent 技能有哪些，包括 ClawdHub 和其他来源的热门技能」

Fast 委派给了 **@researcher**，而非 **@skill-procurement**。

## 日志依据

来自 `~/.openclaw/agents/fast/sessions/1e3f714a-5f0f-432d-ad45-a2002b6be0d1.jsonl`：

```json
"thinking": "用户想让我用工具搜索网上的热门技能，比如 ClawdHub 或其他来源。但我是 Fast agent，我不应该自己去做这种搜索/研究任务。我应该把这个任务派给 researcher 或者 skill-procurement。

根据我的角色定义：
- @researcher 负责\"长文阅读、NotebookLM 和深度信息搜集\"
- @skill-procurement 负责\"找技能、安装技能、技能采购\"

这个任务是搜索网上的热门技能信息，属于信息搜集类的任务，应该派给 @researcher。"
```

Fast 的 tool call：
```json
{"task":"用网络搜索查找目前最热门的 OpenClaw/AI Agent 技能有哪些，包括 ClawdHub 和其他来源的热门技能","agentId":"researcher"}
```

## 根因分析

### 1. 用户表述触发「信息搜集」分类

用户使用了 **「用网络搜索查找」**，Fast 将其理解为：

- 需要 **web_search**（网络搜索）
- 属于 **信息搜集** 类任务

### 2. Fast 的 agent 角色定义

| Agent | 描述（SOUL/AGENTS） |
|-------|---------------------|
| researcher | 长文阅读、NotebookLM、**深度信息搜集** |
| skill-procurement | **找技能**、安装技能、技能采购（skills.sh、ClawdHub） |

### 3. Fast 的决策逻辑

- 看到「网络搜索」→ 联想到 researcher 的 **web_search** 能力
- 将任务归类为「信息搜集」→ 选择 researcher
- 未把「技能」作为主关键词，优先匹配 skill-procurement

### 4. 对比：正确委派给 skill-procurement 的案例

| 用户表述 | 委派目标 |
|----------|----------|
| 帮我找找画图相关的技能 | skill-procurement ✓ |
| 帮我找找有没有关于搜索微信文章相关的技能 | skill-procurement ✓ |
| 帮我搜索一下最热门的技能都有哪些 | skill-procurement ✓ |
| **用网络搜索查找**目前最热门的...技能 | researcher ✗ |

差异在于：前几例没有「用网络搜索」字样，Fast 直接识别为「找技能」→ skill-procurement。

## 结论

**Fast 按「手段」（网络搜索）而不是「目标」（找技能）来选 agent。**

- 用户说「用网络搜索查找」→ Fast 认为需要 web_search → researcher 有 web_search → 派给 researcher
- 用户只说「找技能」「搜索技能」→ Fast 认为需要技能目录搜索 → skill-procurement 负责 → 派给 skill-procurement

## 语义重叠

同一类需求有两种理解方式：

1. **技能目录搜索**：clawdhub search、npx skills find → skill-procurement
2. **网络调研**：web_search 查博客、榜单、社区讨论 → researcher

用户请求同时包含「网络搜索」和「技能」，Fast 选择了「网络搜索」作为主特征，因此派给了 researcher。

## 可选改进方向（不改代码/提示词的前提下）

1. **用户侧**：避免说「用网络搜索查找」，直接说「找最热门的技能」「搜一下 ClawdHub 上最火的技能」等，更容易被派给 skill-procurement。
2. **配置侧**：在 SOUL/AGENTS 中补充规则，例如：凡涉及「技能」「ClawdHub」「skills.sh」的搜索，优先派给 skill-procurement，即使包含「网络搜索」字样。
