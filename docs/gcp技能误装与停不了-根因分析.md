# gcp 技能误装与停不了 — 根因分析

> 基于 2026-03-13 会话日志的深度分析

---

## 一句话说明

你要的是 **gcp-cloud-run**（部署到 Cloud Run），它已经在你 workspace 里了。Clawbot 误装了 **gcp**（通用 GCP 知识）到 skill-procurement 的目录，这是两个不同的技能，装错了。可以删掉误装的 gcp。

---

## 一、现象

1. **误装**：用户要装 `gcp-cloud-run` 技能到 main，Clawbot 却装了 `gcp`（通用 GCP 最佳实践）到 skill-procurement 的 workspace
2. **停不了**：安装或执行过程中的进程无法被停止

---

## 二、根因分析

### 2.1 误装：装错技能 + 装错 workspace

#### 用户请求

- 飞书：`用 gcp-cloud-run 技能部署 firebase-demo 到 Cloud Run`
- 另一会话：`搜索并安装 gcp-cloud-run 技能到 main agent`

#### 实际执行（skill-procurement 会话 f0bc98b4）

| 步骤 | 操作 | 结果 |
|------|------|------|
| 1 | `clawdhub search gcp-cloud-run` | ClawdHub 返回：gcloud, google-workspace-mcp, **gcp**, gcp-fullstack, create-new-openclaw-in-gcp... **无 gcp-cloud-run** |
| 2 | 模型选择 | 选了 `gcp`（Google Cloud 通用最佳实践），而非 gcp-cloud-run |
| 3 | `clawdhub install gcp` | **未传 `--workdir`**，安装到 cwd = `~/.openclaw/workspace-skill-procurement` |
| 4 | 校验 | 校验路径是 skill-procurement 的 skills，未按 main 的 workspace 校验 |

#### 根因拆解

**A. ClawdHub 无 gcp-cloud-run**

- `clawdhub search gcp-cloud-run` 的向量结果里没有名为 `gcp-cloud-run` 的技能
- 最接近的是：gcp、gcp-fullstack、create-new-openclaw-in-gcp
- 文档《skill-procurement安装路径偏差分析》提到的 gcp-cloud-run 可能来自 skills.sh 或旧版 ClawdHub，当前 ClawdHub 可能未收录

**B. 模型选错技能**

- 用户明确要 `gcp-cloud-run`（Cloud Run 部署）
- 模型在搜索结果中选了 `gcp`（通用 GCP 知识）
- 未做「名称精确匹配」或「用途校验」，直接选了相似度最高的 gcp

**C. 安装目标 workspace 错误**

- 用户要求：`安装到 main agent`
- main 的 workspace：`~/.openclaw/workspace-main`（见 openclaw.json）
- 实际执行：`clawdhub install gcp`，无 `--workdir`
- 默认 workdir = cwd = skill-procurement 的 workspace
- 正确应为：`clawdhub install gcp --workdir ~/.openclaw/workspace-main`

**D. skill-procurement SKILL 与配置不一致**

SKILL 中的 Agent Workspace Map：

```
| main | ~/.openclaw/workspace |
| fast | ~/.openclaw/workspace-fast |
| researcher | ~/.openclaw/workspace-researcher |
```

实际 openclaw.json：

```
main: /Users/oscar/.openclaw/workspace-main
fast: /Users/oscar/.openclaw/workspaces/fast
researcher: /Users/oscar/.openclaw/workspaces/researcher
```

- SKILL 写的是 `workspace`，配置是 `workspace-main`
- 即使模型按 SKILL 来，也会指向错误路径

---

### 2.2 停不了：process kill 的限制

#### 代码逻辑（bash-tools.process.ts）

```javascript
case "kill": {
  if (!scopedSession.backgrounded) {
    return {
      content: [{ type: "text", text: `Session ${params.sessionId} is not backgrounded.` }],
      details: { status: "failed" },
    };
  }
  killSession(scopedSession);
  ...
}
```

- `process kill` **只对 backgrounded 会话有效**
- 若 exec 未用 `background: true` 启动，`session` 为 foreground，`process kill` 会直接返回失败

#### 可能的「停不了」场景

1. **非 background 的 exec**：默认 foreground，`process kill` 不可用
2. **/stop 未生效**：agent 收到 /stop 后应 abort，触发 `run.kill()`，但若实现有 bug 或时序问题，可能不会真正 kill
3. **npx skills find 无参数**：会进入 fzf 交互，在非 TTY 下挂起，且难以 kill（文档已提到）

---

## 三、Fast 会话的异常（1e2ff799）

用户请求：`用 gcp-cloud-run 技能部署 firebase-demo 到 Cloud Run`

Fast 应：`sessions_spawn(agentId=main, task="...")` 或派给 skill-procurement

实际：Fast 未派活，直接尝试：

- `read /Users/oscar/.openclaw/skills/gcp-cloud-run/SKILL.md` → ENOENT
- 多次 `process submit` 执行 `clawdhub search gcp-cloud-run`，并不断尝试不同参数（sessionId、cwd、env 等）

Fast 的 tools.deny 里有 `exec`、`shell`，但 `process` 仍可用，导致用 process 间接跑命令，形成死循环式重试。

---

## 四、不改代码的修复与规避

### 4.1 误装：技能与 workspace

1. **确认 gcp-cloud-run 是否存在**
   - 若在 ClawdHub：`clawdhub search gcp-cloud-run` 或 `clawdhub search "cloud run"`
   - 若在 skills.sh：`npx skills find gcp cloud run`（需带参数）
   - 若都不存在，需要用户提供正确来源或 slug

2. **统一 workspace 映射**
   - 在 skill-procurement 的 SKILL 或 USER.md 中写明：main 的 workspace 是 `~/.openclaw/workspace-main`（与 openclaw.json 一致）
   - 强调：安装到 main 时必须用 `--workdir ~/.openclaw/workspace-main`

3. **安装前确认**
   - 要求 skill-procurement：当用户指定技能名（如 gcp-cloud-run）时，必须优先精确匹配 slug，找不到则明确告知「未找到 gcp-cloud-run」

4. **手动修正本次误装**
   ```bash
   # 若希望 gcp 在 main 的 workspace
   cp -r ~/.openclaw/workspace-skill-procurement/skills/gcp ~/.openclaw/workspace-main/skills/
   ```

### 4.2 停不了

1. **长时间任务用 background**
   - 在 skill-procurement 的 SKILL 中说明：`npx skills find`、`clawdhub search` 等可能较慢时，用 `background: true` 启动，便于用 `process kill` 停止

2. **避免无参数 npx skills find**
   - SKILL 已强调：Never run `npx skills find` without arguments
   - 若已挂起：在宿主机用 `ps aux | grep "npx skills"` 找到 pid，`kill -9 <pid>` 手动结束

3. **使用 /stop**
   - 对当前 agent 会话发 `/stop`，应触发 tool call 的 abort，进而 kill 未 background 的 exec（若实现正确）

---

## 五、总结

| 问题 | 根因 | 不改代码的应对 |
|------|------|----------------|
| 装错技能 | ClawdHub 无 gcp-cloud-run；模型选了 gcp | 查清 gcp-cloud-run 来源；SKILL 要求精确匹配 slug |
| 装错 workspace | 未传 `--workdir`；SKILL 与配置不一致 | 在 SKILL 中写清 main=workspace-main；安装时强制 `--workdir` |
| 停不了 | process kill 仅支持 background 会话 | 长任务用 background；避免无参 npx skills find；必要时手动 kill |

---

## 六、直接回答你的问题

### 新装的 gcp 成功了没有？

**安装本身成功了**，但装错了：

- 装的是 **gcp**（通用 GCP 知识：成本、安全、网络等），不是你要的 **gcp-cloud-run**（部署到 Cloud Run）
- 装到了 **skill-procurement 的 workspace**（`~/.openclaw/workspace-skill-procurement/skills/gcp`），不是 main

### 是不是重复了？

**不是重复**。这是两个不同的技能：

| 技能 | 位置 | 用途 |
|------|------|------|
| **gcp-cloud-run** | `~/.openclaw/workspace/skills/gcp-cloud-run` | 部署容器到 Cloud Run，有 gcloud 命令、Quick Start |
| **gcp** | `~/.openclaw/workspace-skill-procurement/skills/gcp` | GCP 通用最佳实践（成本陷阱、安全规则、网络等知识） |

你要的 gcp-cloud-run 本来就在 workspace 里，这次误装的是另一个技能 gcp。

### 要不要移除？

**建议移除**。理由：

1. 你不需要在 skill-procurement 里用 GCP 知识，skill-procurement 的职责是找技能、装技能
2. 误装的 gcp 对「部署 firebase-demo 到 Cloud Run」没有帮助
3. 留着只会占用空间，还可能让后续 agent 混淆

**移除命令：**

```bash
rm -rf ~/.openclaw/workspace-skill-procurement/skills/gcp
```
