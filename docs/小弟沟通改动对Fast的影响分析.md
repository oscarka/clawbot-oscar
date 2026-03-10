# 小弟沟通改动对 Fast 的影响分析（深度版）

> 针对本次「增加小弟沟通」（[接活]、[进度]、[超时]）改动的专项分析，厘清对 Fast 的直接影响与**间接影响**。

---

## 一、本次改动范围（仅限本次会话）

### 1.1 实际修改的文件

| 文件 | 改动内容 |
|------|----------|
| **subagent-internal-comm.ts** | 新增 `maybeSendInternalCommAccept`、`maybeSendInternalCommProgress`、`maybeSendInternalCommTimeout` |
| **subagent-registry.ts** | ① lifecycle `phase=start` 时调用 [接活]；② 新增进度检查器（定时跑、发 [进度]/[超时]）；③ `registerSubagentRun` 时启动 progress checker |
| **config (types + zod)** | 新增 `progressCheckIntervalMinutes`、`progressCheckThresholdMinutes`、`runTimeoutMinutes` |
| **默认值** | `progressCheckIntervalMinutes` 默认从 0 改为 5 |
| **文档** | subagents.md、上下对齐与任务监控方案.md |

### 1.2 未修改的文件

| 文件 | 说明 |
|------|------|
| **system-prompt.ts** | 未改动。Fast 的 sessions_spawn 块、toolNames 分支等来自 359eaeb，非本次 |
| **sessions-spawn-tool.ts** | 未改动。[派活] 的 `maybeSendInternalCommSpawn` 原本就有 |
| **subagent-announce.ts** | 未改动。[回报] 的 `maybeSendInternalCommAnnounce` 原本就有 |

---

## 二、架构前提：共享进程与事件循环

- **Gateway 进程**：单进程 Node.js，所有 agent 运行、Gateway RPC、定时器、WebSocket 共享同一事件循环
- **Main 与 Subagent  lane**：独立队列，可并发（main 默认 4，subagent 默认 8）
- **Fast**：跑在 main lane；**researcher/main**：跑在 subagent lane
- **callGateway**：每次调用新建 WebSocket 连接，请求 Gateway 自身；`send`、`agent.wait` 等均走此路径

---

## 三、对 Fast 的直接影响

### 3.1 无直接影响

| 项目 | 说明 |
|------|------|
| **sessions_spawn 工具** | 未改，Fast 调用方式、参数、返回格式均不变 |
| **Fast 的 system prompt** | 未改，token 数、指令内容均不变 |
| **派活阻塞** | [派活] 仍是 `void sendToInternalGroup`，不阻塞 |
| **接活** | [接活] 在子 agent lifecycle `start` 时发，与 Fast 的 tool 调用无关，不阻塞 Fast |
| **进度 / 超时** | 由定时器在后台跑，与 Fast 的请求路径完全分离 |

### 3.2 唯一新增的同步逻辑

在 `registerSubagentRun` 中：

- 调用 `startProgressChecker()`（若 `progressCheckIntervalMinutes > 0`）
- 内部：`setInterval(() => void runProgressCheck(), 300000)`
- 不 await、不阻塞，对 Fast 的 tool 返回延迟可忽略

---

## 四、对 Fast 的间接影响（深入分析）

### 4.1 共享事件循环上的同步阻塞

**关键事实**：`persistSubagentRuns()` 使用 `saveJsonFile` → `fs.writeFileSync`，**同步**阻塞事件循环。

| 调用点 | 调用时机 | 阻塞对象 |
|--------|----------|----------|
| 1. lifecycle `phase=start` | 子 agent 真正开始跑时，`emitAgentEvent` 同步调用所有 listener | 子 agent 所在 lane（subagent） |
| 2. lifecycle `phase=end/error` | 子 agent 结束时 | 同上 |
| 3. `runProgressCheck` | 每 5 分钟定时器触发 | 任意正在执行的 agent（main 或 subagent） |
| 4. `registerSubagentRun` | Fast 调用 sessions_spawn 时 | 当前 Fast 所在 lane（main） |

**本次改动新增的 persist 调用**：

- **lifecycle start**：`phase === "start"` 时，先 `entry.startedAt = startedAt`，再 `persistSubagentRuns()`，再 `maybeSendInternalCommAccept`
- **runProgressCheck**：每次发 [进度] 或 [超时] 后，更新 `lastProgressSentAt` 或 `endedAt`，再 `persistSubagentRuns()`

**影响**：每次 `persistSubagentRuns()` 都会阻塞整个 event loop 若干 ms（取决于 runs.json 大小和磁盘 I/O）。若 Fast 在 main lane 正在跑、子 agent 在 subagent lane 正在跑，而 progress checker 或 lifecycle 回调触发 persist，二者会**竞争**同一事件循环。

---

### 4.2 进度检查器与事件循环竞争

**`runProgressCheck`** 每 5 分钟执行一次：

```ts
for (const [runId, entry] of subagentRuns.entries()) {
  // ...
  if (runningMinutes >= timeoutMinutes) {
    maybeSendInternalCommTimeout(...);
    entry.endedAt = now;
    persistSubagentRuns();  // 同步
    void runSubagentAnnounceFlow(...);
  }
  if (runningMinutes >= thresholdMinutes) {
    maybeSendInternalCommProgress(...);
    entry.lastProgressSentAt = now;
    persistSubagentRuns();  // 同步
  }
}
```

- 若存在多个长时间运行的 subagent，一次 progress check 可能触发多次 `persistSubagentRuns()`
- 每次 persist 都是同步磁盘写，阻塞 event loop
- **默认值**：`progressCheckIntervalMinutes = 5`（之前为 0，即不启动）→ 现在每次派活都会启动 progress checker，定时任务持续存在

---

### 4.3 lifecycle 回调中的同步工作

**`emitAgentEvent`** 是同步的：遍历所有 listener，依次调用，**不 await**。

`subagent-registry` 的 listener 在 `phase === "start"` 时：

```ts
entry.startedAt = startedAt;
persistSubagentRuns();  // 同步，阻塞
maybeSendInternalCommAccept(...);  // void sendToInternalGroup，不阻塞
```

- `persistSubagentRuns()` 在 emit 的同步路径中执行，会阻塞**当前 emit 所在的 run**（即 subagent）
- 子 agent 在 subagent lane 跑；Fast 在 main lane。两者理论上可并发，但**共享同一 event loop**
- 若 subagent 正在 emit lifecycle start，此时 main lane 若有 Fast 在等待 LLM 流式输出或下一个 tick，**不会**被直接阻塞；但若 main 和 subagent 恰好同时需要 CPU（例如都在做同步计算），event loop 被 persist 占用的时间会延迟所有其他任务

---

### 4.4 `loadConfig` 的调用频率

`loadConfig()` **无缓存**：每次调用都会 `readFileSync` + `parse` + `validate`。

**本次改动新增调用**：

- `resolveProgressCheckIntervalMs`、`resolveProgressCheckThresholdMinutes`、`resolveRunTimeoutMinutes`：在 `runProgressCheck` 中每次调用
- `resolveInternalCommGroup`：在 `maybeSendInternalCommAccept`、`maybeSendInternalCommProgress`、`maybeSendInternalCommTimeout` 中每次调用，内部会 `loadConfig()`

**影响**：每次 [接活]、[进度]、[超时] 发送前都会 `loadConfig()`，同步读盘 + 解析。若配置较大，会进一步增加 event loop 阻塞时间。

---

### 4.5 内部通信的 `callGateway` 竞争

`sendToInternalGroup` 调用 `callGateway({ method: "send", ... })`：

- 新建 WebSocket 连接，请求 Gateway 自身
- Gateway 的 `send` handler 会 `await deliverOutboundPayloads`（如 Feishu API）
- 该过程不阻塞 emit 的同步路径（`void`），但会占用 event loop 的异步任务

**竞争**：Gateway 同时要处理：

- Fast 的 agent run（main lane）
- 子 agent 的 run（subagent lane）
- [派活]、[接活]、[进度]、[超时]、[回报] 的 `send` 请求
- 其他 channel 的 inbound/outbound

所有请求共享同一进程和 event loop。若 Feishu 或其他 channel 的 `send` 较慢，会占用更多 event loop 时间，间接影响 Fast 的调度。

---

### 4.6 默认值变更：progress checker 持续运行

**之前**：`progressCheckIntervalMinutes` 默认 0 → 不启动 progress checker。

**现在**：默认 5 → 每次 `registerSubagentRun` 时启动 `startProgressChecker()`，定时器每 5 分钟跑一次。

**影响**：只要存在过 subagent 派活，progress checker 就会一直存在，每 5 分钟执行一次 `runProgressCheck`，直到 `subagentRuns.size === 0` 才 `stopProgressChecker()`。若长时间有 subagent 在跑，会定期产生 persist 和可能的 [进度]/[超时] 发送，增加 event loop 负载。

---

## 五、间接影响小结

| 维度 | 机制 | 对 Fast 的影响 |
|------|------|----------------|
| **同步 persist** | `fs.writeFileSync` 阻塞 event loop | 与 persist 同时发生的其他任务（含 Fast）可能被延迟数 ms |
| **lifecycle start 时 persist** | 子 agent 每次 start 都 persist | 子 agent 在 subagent lane 跑；与 Fast 共享 event loop，存在间接竞争 |
| **progress checker 定时 persist** | 每 5 分钟，可能多次 persist | 若 Fast 在 run 时碰上 progress check，会短暂被阻塞 |
| **loadConfig 无缓存** | 每次 internal comm 都读配置 | 增加同步 I/O，放大 event loop 阻塞 |
| **send 请求竞争** | [接活]/[进度]/[超时] 的 callGateway 与 Fast 共享 Gateway | 增加异步任务排队，可能延迟 Fast 的调度 |
| **progress checker 默认开启** | 从 0 改为 5，定时任务持续存在 | 增加长期进程的周期性负载 |

---

## 六、与「变慢」的关系

用户文档《分配任务与小弟回复改动后的变慢根因分析》中的结论：

- **主因**：system-prompt 膨胀（359eaeb 的 toolNames 分支、NotebookLM 等）
- **次因**：队列 collect + debounce
- **非主因**：sessions_spawn、internalComm 均为异步，不阻塞主流程

**本次「增加小弟沟通」改动的补充**：

- 未改 system-prompt、未改队列
- 但**新增**了多处同步 persist、lifecycle 回调内 persist、以及默认开启的 progress checker
- 这些都会在 event loop 上产生**同步阻塞**和**周期性负载**，与 Fast 共享同一进程

**结论**：本次改动对 Fast 的间接影响是**真实存在**的，但量级通常为：

- 单次 persist：ms 级
- 单次 loadConfig：ms 级（取决于配置大小）
- 每 5 分钟一次 progress check：若 runs 不多，影响有限

在**高并发、多 subagent、长时间运行**的场景下，这些累积会放大为可感知的延迟。在**单次派活、短时运行**的场景下，影响较小。

---

## 七、Fast 与各消息的时序关系

```
时间线（Fast 派活给 main）：

T0     Fast 调用 sessions_spawn
T0+    [派活] 发出（sessions_spawn 内，void）
T0+    sessions_spawn 返回，Fast 继续生成
T1     main 的 lifecycle start 事件到达
T1+    persistSubagentRuns() 同步执行 ← 阻塞 event loop
T1+    [接活] 发出（void，异步）
T2     Fast 已回复用户（与 T1 无关）
...
T5min  进度检查器第一次跑
T5min+ 可能多次 persistSubagentRuns() ← 阻塞 event loop
T5min+ [进度] 发出（若 main 仍在跑）
...
Tend   main 结束，[回报] 发出
```

Fast 的回复只依赖 T0 附近的 sessions_spawn 返回，与 [接活]、[进度]、[回报] 的发送时间无关。但**间接**地，T1、T5min 等时刻的 persist 和 loadConfig 会占用 event loop，若 Fast 正在执行，可能被短暂延迟。

---

## 八、已知问题（与 Fast 无关）

| 问题 | 说明 |
|------|------|
| **恢复后无 [进度]** | Gateway 重启后，`restoreSubagentRunsOnce` 未调用 `startProgressChecker()`，恢复的 runs 不会收到 [进度] |
| **20a47b05 无进度** | 符合上述恢复逻辑缺陷，与 Fast 行为无关 |

---

## 九、建议（仅分析，不修改代码）

若后续优化，可考虑：

1. **persist 异步化**：`persistSubagentRuns` 改为 `fs.promises.writeFile`，避免阻塞 event loop
2. **loadConfig 缓存**：对 internal comm 路径的配置读取做短期缓存或复用
3. **progress check 节流**：避免单次 progress check 内多次 persist，可合并为一次批量写入
4. **progress checker 默认值**：若用户不依赖 [进度]，可将 `progressCheckIntervalMinutes` 默认改回 0，减少长期进程的周期性负载
