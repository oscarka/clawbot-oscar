# 派活 Dispatch 子系统设计

> 任务先于执行，系统为真相来源。借鉴 Cron / NotebookLM 模式，解决 Fast 假装派活问题。

**状态**：设计稿，待评审  
**关联文档**：[Fast假装派活-根因分析](./Fast假装派活-根因分析.md)、[上下对齐与任务监控方案](./上下对齐与任务监控方案.md)

---

## 一、背景与问题

### 1.1 现状

用户让 Fast「派给 main 做 X」，可能出现：

- Fast 只说「📋 已派给 @main」，但**没有调用 `sessions_spawn`**
- 说和做脱节：模型把「描述动作」当成「执行动作」
- 提示词只对 researcher 强调必须调工具，main / skill-procurement 无同等约束

详见 [Fast假装派活-根因分析](./Fast假装派活-根因分析.md)。

### 1.2 现有方案局限

| 方案 | 做法 | 局限 |
|------|------|------|
| 提示词扩展 | 要求所有派活都必须调 sessions_spawn | 依赖模型遵守，模型仍可能只说不做 |
| 派活检测 | 检测「已派给」但无 sessions_spawn → 补救 | 事后补救，时机可能错过；检测规则易漏 |

**本质**：真相来源是「模型有没有调工具」，而模型行为不可靠。

### 1.3 设计目标

1. **任务先于执行**：先建任务记录（带 taskId），再执行
2. **系统为真相来源**：「已派给」由系统根据任务记录生成，不信任模型文本
3. **单一入口**：派活只能通过 `dispatch.create`，Fast 不能直接调用 `sessions_spawn`
4. **可追踪**：[派活][接活][进度][回报] 都带 taskId，形成完整链路

---

## 二、启发：Cron 与 NotebookLM

### 2.1 Cron

| 环节 | 说明 |
|------|------|
| 任务定义 | `jobs.json` 中先有 job（带 id） |
| 触发 | 定时器根据 schedule 触发 |
| 执行 | 由系统执行，不依赖「谁说了什么」 |

**结论**：任务记录是唯一真相来源。

### 2.2 NotebookLM

| 环节 | 说明 |
|------|------|
| 创建 | `submit(task)` → 返回 `task_id` |
| 执行 | 后台异步执行 |
| 追踪 | `get_task(task_id)` 查状态 |

**结论**：先有任务记录、拿到 ID，再执行和追踪。

### 2.3 共性

| 特性 | Cron | NotebookLM | 派活（目标） |
|------|------|------------|--------------|
| 任务先于执行 | ✓ | ✓ | ✓ |
| 记录带 ID | job.id | task_id | taskId |
| 系统管理生命周期 | ✓ | ✓ | ✓ |
| 不依赖「谁说了什么」 | ✓ | ✓ | ✓ |

---

## 三、架构设计

### 3.1 核心原则

1. **任务记录 = 唯一真相**：有任务记录 = 一定派了；没有 = 一定没派
2. **单一入口**：派活只能通过 `dispatch.create`，不能直接 `sessions_spawn`
3. **系统生成对外宣称**：只有 `dispatch.create` 成功后才生成「已派给 @main，TaskId: xxx」
4. **拦截错误宣称**：若回复里有「已派给」类字样，但本 turn 没有 `dispatch.create` 调用 → 删除或替换

### 3.2 数据流

```
用户请求
    ↓
Fast 调用 dispatch.create(task, agentId)
    ↓
┌─────────────────────────────────────────────────────────┐
│ dispatch.create 内部                                     │
│  1. 创建任务记录 (taskId, task, agentId, status, ...)   │
│  2. 调用 sessions_spawn (内部，不暴露给 Fast)            │
│  3. 关联 taskId ↔ childSessionKey / runId               │
│  4. 发送 [派活] 到小弟群（带 taskId）                     │
│  5. 返回 { status, taskId, childSessionKey }             │
└─────────────────────────────────────────────────────────┘
    ↓
系统生成「已派给 @main，TaskId: xxx」注入回复或单独发送
    ↓
main 接活 → [接活]（带 taskId）
    ↓
进度 → [进度]（带 taskId）
    ↓
回报 → [回报]（带 taskId）
```

### 3.3 任务记录

| 字段 | 类型 | 说明 |
|------|------|------|
| taskId | string | 唯一标识，如 `dispatch-{uuid}` |
| task | string | 任务描述 |
| agentId | string | 目标 agent |
| status | enum | `created` \| `spawned` \| `accepted` \| `running` \| `completed` \| `failed` \| `timeout` |
| requesterSessionKey | string | 发起方会话 |
| childSessionKey | string? | 子会话 key（spawn 后填充） |
| runId | string? | agent run 的 runId |
| createdAt | number | 创建时间戳 |
| spawnedAt | number? | 派活发送时间 |
| acceptedAt | number? | 接活时间 |
| completedAt | number? | 完成时间 |

### 3.4 工具接口

#### dispatch.create（新工具，替代 sessions_spawn 给 Fast 用）

```ts
// 参数
{
  task: string;      // 必填
  agentId: string;   // 必填
  label?: string;   // 可选
  // 其他与 sessions_spawn 兼容的参数（model, thinking, runTimeoutSeconds 等）
}

// 返回
{
  status: "accepted" | "error";
  taskId: string;           // 任务记录 ID
  childSessionKey?: string;
  runId?: string;
  error?: string;
}
```

**内部逻辑**：

1. 生成 taskId
2. 写入任务记录（status: created）
3. 调用内部 sessions_spawn（或等价逻辑）
4. 更新任务记录（childSessionKey, runId, status: spawned）
5. 发送 [派活] 到小弟群（带 taskId）
6. 返回 taskId 等

#### dispatch.status（可选，用于查询）

```ts
// 参数
{ taskId: string }

// 返回
{ taskId, status, childSessionKey, ... }
```

### 3.5 工具策略

| Agent | sessions_spawn | dispatch.create |
|-------|----------------|-----------------|
| Fast | **deny** | allow |
| main | allow | deny（或 allow，按需） |
| researcher | allow | deny |
| skill-procurement | allow | deny |
| cron / hook | 直接调用内部 spawn，不经过 dispatch | - |

**说明**：Fast 只能调用 `dispatch.create`，不能直接 `sessions_spawn`。其他 agent 若需要派子任务，可继续用 `sessions_spawn`（或未来统一到 dispatch）。

---

## 四、对外宣称与拦截

### 4.1 系统生成「已派给」

**时机**：`dispatch.create` 成功返回后

**方式**（二选一或组合）：

- **A. 注入回复**：在 Fast 的最终回复前/后追加系统生成的一句：「已派给 @main，TaskId: xxx」
- **B. 单独发送**：通过 internalComm 或等价渠道，单独发一条「已派给 @main，TaskId: xxx」

**格式**：`已派给 @{agentId}，TaskId: {taskId}`

### 4.2 拦截错误宣称

**触发条件**：Fast 的回复中包含「已派给」「交给」「指派」等字样，且本 turn 没有 `dispatch.create` 调用

**处理**（三选一）：

| 方案 | 做法 | 优点 | 缺点 |
|------|------|------|------|
| A. 删除 | 删除或屏蔽该句 | 干净 | 可能影响上下文连贯 |
| B. 替换 | 替换为「未实际派活，请重试」 | 明确 | 需用户再操作 |
| C. 追加 | 不删，追加「（未实际派活）」 | 保留原意 | 可能显得冗长 |

**建议**：先实现 A（删除），若影响体验再考虑 B/C。

**实现位置**：回复后处理（reply post-processing），在发送到渠道前检查并修改。

### 4.3 禁止模型宣称（可选）

在 Fast 的 system prompt 中明确：

- 禁止写「已派给」「交给」「指派」等字样
- 派活时只需调用 `dispatch.create`，系统会自动生成「已派给」并发送

**优先级**：可放在拦截之后，作为双重保障。

---

## 五、与现有组件的衔接

### 5.1 与 sessions_spawn 的关系

| 场景 | 处理 |
|------|------|
| Fast 派活 | 调用 `dispatch.create` → 内部调用 `sessions_spawn`（或复用其逻辑） |
| 其他 agent 派活 | 继续用 `sessions_spawn`（或逐步迁移到 dispatch） |
| cron / hook 直接跑 main | 不经过 Fast，直接 spawn，无需 dispatch |

### 5.2 与 subagent-registry 的关系

- `subagent-registry` 仍以 runId / childSessionKey 为 key 追踪 run
- dispatch 任务记录与 subagent run 通过 `childSessionKey` / `runId` 关联
- [接活][进度][回报] 由 subagent-registry 触发时，需带上 taskId（若存在）

### 5.3 与 internalComm 的关系

- [派活] 由 dispatch 发送，格式增加 `TaskId: {taskId}`
- [接活][进度][超时][回报] 由 subagent-registry 触发，内部 comm 需支持传入 taskId 并写入消息

**示例**：

```
[派活] @main
TaskId: dispatch-abc123
任务：手动触发小红书任务
Session: agent:main:subagent:xxx-xxx-xxx
```

---

## 六、任务记录存储

### 6.1 存储方式

| 选项 | 说明 |
|------|------|
| 内存 + 持久化 | 与 subagent-registry 类似，内存 Map + 定期落盘 |
| 独立文件 | `~/.openclaw/dispatch-tasks.json` 或按 taskId 分文件 |
| 复用 subagent-registry | 扩展 SubagentRunRecord，增加 taskId 字段，dispatch 创建时写入 |

**建议**：先采用「扩展 SubagentRunRecord + taskId」，dispatch 创建任务时先写一条带 taskId 的记录，再调用 spawn，spawn 成功后将 childSessionKey 等关联回任务记录。这样最小化新增存储。

### 6.2 生命周期

| 阶段 | 说明 |
|------|------|
| 创建 | dispatch.create 被调用 |
| 派活 | sessions_spawn 成功，[派活] 已发送 |
| 接活 | run 进入 start 阶段，[接活] 已发送 |
| 运行 | 可选 [进度] |
| 完成 | run 结束，[回报] 已发送 |
| 清理 | 任务记录保留一段时间后归档或删除（可配置） |

---

## 七、配置项

| 配置项 | 类型 | 说明 |
|--------|------|------|
| agents.defaults.subagents.dispatch.enabled | boolean | 是否启用 dispatch 模式（默认 true 时 Fast 禁用 sessions_spawn） |
| agents.defaults.subagents.dispatch.interceptWrongClaim | boolean | 是否拦截「已派给」但无 dispatch 的回复（默认 true） |
| agents.defaults.subagents.dispatch.taskRetentionMinutes | number | 任务记录保留时长（默认 1440 = 24h） |

---

## 八、实施顺序

| 阶段 | 内容 | 依赖 |
|------|------|------|
| 1 | 任务记录模型 + 存储 | 无 |
| 2 | dispatch.create 工具实现 | 内部调用 sessions_spawn |
| 3 | Fast 的 sessions_spawn → deny，dispatch.create → allow | 工具策略 |
| 4 | [派活] 消息带 taskId | internalComm |
| 5 | 系统生成「已派给」并注入/发送 | 回复后处理 |
| 6 | 拦截错误宣称 | 回复后处理 |
| 7 | [接活][进度][回报] 带 taskId | subagent-registry + internalComm |

---

## 九、边界与注意事项

| 场景 | 说明 |
|------|------|
| **Cron 直接跑 main** | 不经过 Fast，无 dispatch。可选：cron 触发时也创建一条 dispatch 任务记录并发 [派活]，便于统一追踪。 |
| **其他渠道（非飞书）** | 系统生成「已派给」的注入/发送需适配各渠道。 |
| **向后兼容** | 若 `dispatch.enabled: false`，Fast 仍可用 sessions_spawn，行为与当前一致。 |
| **多 Agent** | researcher、skill-procurement 等若需派活，可逐步迁移到 dispatch，或保持 sessions_spawn。 |

---

## 十、小结

| 项目 | 说明 |
|------|------|
| **核心** | 任务先于执行；系统为真相来源；单一入口 dispatch.create |
| **借鉴** | Cron / NotebookLM 的「先有记录再执行」模式 |
| **解决** | Fast 假装派活 — 模型无法宣称「已派给」而不调用工具，因为 Fast 只能调 dispatch.create |
| **衔接** | 与 sessions_spawn、subagent-registry、internalComm 兼容 |
| **实施** | 分阶段，可配置，向后兼容 |
