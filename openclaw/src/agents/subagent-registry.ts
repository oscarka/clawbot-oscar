import { loadConfig } from "../config/config.js";
import { callGateway } from "../gateway/call.js";
import { onAgentEvent } from "../infra/agent-events.js";
import { resolveAgentIdFromSessionKey } from "../routing/session-key.js";
import { type DeliveryContext, normalizeDeliveryContext } from "../utils/delivery-context.js";
import { runSubagentAnnounceFlow, type SubagentRunOutcome } from "./subagent-announce.js";
import {
  maybeSendInternalCommAccept,
  maybeSendInternalCommProgress,
  maybeSendInternalCommTimeout,
} from "./subagent-internal-comm.js";
import {
  loadSubagentRegistryFromDisk,
  saveSubagentRegistryToDisk,
  saveSubagentRegistryToDiskAsync,
} from "./subagent-registry.store.js";
import { resolveAgentTimeoutMs } from "./timeout.js";

export type SubagentRunRecord = {
  runId: string;
  childSessionKey: string;
  requesterSessionKey: string;
  requesterOrigin?: DeliveryContext;
  requesterDisplayKey: string;
  task: string;
  cleanup: "delete" | "keep";
  label?: string;
  createdAt: number;
  startedAt?: number;
  endedAt?: number;
  outcome?: SubagentRunOutcome;
  archiveAtMs?: number;
  cleanupCompletedAt?: number;
  cleanupHandled?: boolean;
  /** When [进度] was last sent; used to throttle progress messages. */
  lastProgressSentAt?: number;
};

const subagentRuns = new Map<string, SubagentRunRecord>();
let sweeper: NodeJS.Timeout | null = null;
let progressChecker: NodeJS.Timeout | null = null;
let listenerStarted = false;
let listenerStop: (() => void) | null = null;
// Use var to avoid TDZ when init runs across circular imports during bootstrap.
var restoreAttempted = false;

let pendingPersist: Promise<void> | null = null;

function persistSubagentRuns() {
  if (pendingPersist) return;
  pendingPersist = (async () => {
    await new Promise<void>((r) => setImmediate(r));
    try {
      await saveSubagentRegistryToDiskAsync(subagentRuns);
    } catch {
      // ignore persistence failures
    }
  })();
  pendingPersist.finally(() => {
    pendingPersist = null;
  });
}

/** Wait for any pending async persist to complete. Use in tests. */
export async function flushSubagentRegistryPersist(): Promise<void> {
  if (pendingPersist) await pendingPersist;
}

const resumedRuns = new Set<string>();

function resumeSubagentRun(runId: string) {
  if (!runId || resumedRuns.has(runId)) return;
  const entry = subagentRuns.get(runId);
  if (!entry) return;
  if (entry.cleanupCompletedAt) return;

  if (typeof entry.endedAt === "number" && entry.endedAt > 0) {
    if (!beginSubagentCleanup(runId)) return;
    const requesterOrigin = normalizeDeliveryContext(entry.requesterOrigin);
    void runSubagentAnnounceFlow({
      childSessionKey: entry.childSessionKey,
      childRunId: entry.runId,
      requesterSessionKey: entry.requesterSessionKey,
      requesterOrigin,
      requesterDisplayKey: entry.requesterDisplayKey,
      task: entry.task,
      timeoutMs: 30_000,
      cleanup: entry.cleanup,
      waitForCompletion: false,
      startedAt: entry.startedAt,
      endedAt: entry.endedAt,
      label: entry.label,
      outcome: entry.outcome,
    }).then((didAnnounce) => {
      finalizeSubagentCleanup(runId, entry.cleanup, didAnnounce);
    });
    resumedRuns.add(runId);
    return;
  }

  // Wait for completion again after restart.
  const cfg = loadConfig();
  const waitTimeoutMs = resolveSubagentWaitTimeoutMs(cfg, undefined);
  void waitForSubagentCompletion(runId, waitTimeoutMs);
  resumedRuns.add(runId);
}

function restoreSubagentRunsOnce() {
  if (restoreAttempted) return;
  restoreAttempted = true;
  try {
    const restored = loadSubagentRegistryFromDisk();
    if (restored.size === 0) return;
    for (const [runId, entry] of restored.entries()) {
      if (!runId || !entry) continue;
      // Keep any newer in-memory entries.
      if (!subagentRuns.has(runId)) {
        subagentRuns.set(runId, entry);
      }
    }

    // Resume pending work.
    ensureListener();
    if ([...subagentRuns.values()].some((entry) => entry.archiveAtMs)) {
      startSweeper();
    }
    for (const runId of subagentRuns.keys()) {
      resumeSubagentRun(runId);
    }
  } catch {
    // ignore restore failures
  }
}

function resolveArchiveAfterMs(cfg?: ReturnType<typeof loadConfig>) {
  const config = cfg ?? loadConfig();
  const minutes = config.agents?.defaults?.subagents?.archiveAfterMinutes ?? 60;
  if (!Number.isFinite(minutes) || minutes <= 0) return undefined;
  return Math.max(1, Math.floor(minutes)) * 60_000;
}

function resolveProgressCheckIntervalMs(cfg?: ReturnType<typeof loadConfig>): number {
  const config = cfg ?? loadConfig();
  const minutes = config.agents?.defaults?.subagents?.progressCheckIntervalMinutes ?? 5;
  if (!Number.isFinite(minutes) || minutes <= 0) return 0;
  return Math.max(1, Math.floor(minutes)) * 60_000;
}

function resolveProgressCheckThresholdMinutes(cfg?: ReturnType<typeof loadConfig>): number {
  const config = cfg ?? loadConfig();
  const minutes = config.agents?.defaults?.subagents?.progressCheckThresholdMinutes ?? 5;
  return Number.isFinite(minutes) && minutes > 0 ? Math.floor(minutes) : 5;
}

function resolveRunTimeoutMinutes(cfg?: ReturnType<typeof loadConfig>): number {
  const config = cfg ?? loadConfig();
  const minutes = config.agents?.defaults?.subagents?.runTimeoutMinutes ?? 30;
  return Number.isFinite(minutes) && minutes > 0 ? Math.floor(minutes) : 30;
}

function resolveSubagentWaitTimeoutMs(
  cfg: ReturnType<typeof loadConfig>,
  runTimeoutSeconds?: number,
) {
  return resolveAgentTimeoutMs({ cfg, overrideSeconds: runTimeoutSeconds });
}

function startSweeper() {
  if (sweeper) return;
  sweeper = setInterval(() => {
    void sweepSubagentRuns();
  }, 60_000);
  sweeper.unref?.();
}

function stopSweeper() {
  if (!sweeper) return;
  clearInterval(sweeper);
  sweeper = null;
}

async function sweepSubagentRuns() {
  const now = Date.now();
  let mutated = false;
  for (const [runId, entry] of subagentRuns.entries()) {
    if (!entry.archiveAtMs || entry.archiveAtMs > now) continue;
    subagentRuns.delete(runId);
    mutated = true;
    try {
      await callGateway({
        method: "sessions.delete",
        params: { key: entry.childSessionKey, deleteTranscript: true },
        timeoutMs: 10_000,
      });
    } catch {
      // ignore
    }
  }
  if (mutated) persistSubagentRuns();
  if (subagentRuns.size === 0) stopSweeper();
}

function startProgressChecker() {
  if (progressChecker) return;
  const intervalMs = resolveProgressCheckIntervalMs();
  if (intervalMs <= 0) return;
  progressChecker = setInterval(() => {
    void runProgressCheck();
  }, intervalMs);
  progressChecker.unref?.();
}

function stopProgressChecker() {
  if (!progressChecker) return;
  clearInterval(progressChecker);
  progressChecker = null;
}

async function runProgressCheck() {
  const cfg = loadConfig();
  const thresholdMinutes = resolveProgressCheckThresholdMinutes(cfg);
  const timeoutMinutes = resolveRunTimeoutMinutes(cfg);
  const intervalMs = resolveProgressCheckIntervalMs(cfg);
  const now = Date.now();
  const agentId = (entry: SubagentRunRecord) => resolveAgentIdFromSessionKey(entry.childSessionKey);

  for (const [runId, entry] of subagentRuns.entries()) {
    if (entry.endedAt || entry.cleanupCompletedAt) continue;
    const startedAt = entry.startedAt ?? entry.createdAt;
    const runningMs = now - startedAt;
    const runningMinutes = Math.floor(runningMs / 60_000);

    if (runningMinutes >= timeoutMinutes) {
      maybeSendInternalCommTimeout({
        task: entry.task,
        agentId: agentId(entry),
        childSessionKey: entry.childSessionKey,
        label: entry.label,
      });
      entry.endedAt = now;
      entry.outcome = { status: "timeout" };
      persistSubagentRuns();
      if (!beginSubagentCleanup(runId)) continue;
      const requesterOrigin = normalizeDeliveryContext(entry.requesterOrigin);
      void runSubagentAnnounceFlow({
        childSessionKey: entry.childSessionKey,
        childRunId: entry.runId,
        requesterSessionKey: entry.requesterSessionKey,
        requesterOrigin,
        requesterDisplayKey: entry.requesterDisplayKey,
        task: entry.task,
        timeoutMs: 30_000,
        cleanup: entry.cleanup,
        waitForCompletion: false,
        startedAt: entry.startedAt,
        endedAt: entry.endedAt,
        label: entry.label,
        outcome: entry.outcome,
      }).then((didAnnounce) => {
        finalizeSubagentCleanup(runId, entry.cleanup, didAnnounce);
      });
      continue;
    }

    if (runningMinutes >= thresholdMinutes) {
      const lastSent = entry.lastProgressSentAt ?? 0;
      if (now - lastSent >= (intervalMs || 60_000)) {
        maybeSendInternalCommProgress({
          task: entry.task,
          agentId: agentId(entry),
          childSessionKey: entry.childSessionKey,
          label: entry.label,
          runningMinutes,
        });
        entry.lastProgressSentAt = now;
        persistSubagentRuns();
      }
    }
  }
  if (subagentRuns.size === 0) stopProgressChecker();
}

function ensureListener() {
  if (listenerStarted) {
    return;
  }
  listenerStarted = true;
  listenerStop = onAgentEvent((evt) => {
    if (!evt || evt.stream !== "lifecycle") return;
    const entry = subagentRuns.get(evt.runId);
    if (!entry) {
      return;
    }
    const phase = evt.data?.phase;
    if (phase === "start") {
      const startedAt =
        typeof evt.data?.startedAt === "number" ? (evt.data.startedAt as number) : undefined;
      if (startedAt) {
        entry.startedAt = startedAt;
        persistSubagentRuns();
      }
      maybeSendInternalCommAccept({
        task: entry.task,
        agentId: resolveAgentIdFromSessionKey(entry.childSessionKey),
        childSessionKey: entry.childSessionKey,
        label: entry.label,
      });
      return;
    }
    if (phase !== "end" && phase !== "error") return;
    const endedAt =
      typeof evt.data?.endedAt === "number" ? (evt.data.endedAt as number) : Date.now();
    entry.endedAt = endedAt;
    if (phase === "error") {
      const error = typeof evt.data?.error === "string" ? (evt.data.error as string) : undefined;
      entry.outcome = { status: "error", error };
    } else {
      entry.outcome = { status: "ok" };
    }
    persistSubagentRuns();

    if (!beginSubagentCleanup(evt.runId)) {
      return;
    }
    const requesterOrigin = normalizeDeliveryContext(entry.requesterOrigin);
    void runSubagentAnnounceFlow({
      childSessionKey: entry.childSessionKey,
      childRunId: entry.runId,
      requesterSessionKey: entry.requesterSessionKey,
      requesterOrigin,
      requesterDisplayKey: entry.requesterDisplayKey,
      task: entry.task,
      timeoutMs: 30_000,
      cleanup: entry.cleanup,
      waitForCompletion: false,
      startedAt: entry.startedAt,
      endedAt: entry.endedAt,
      label: entry.label,
      outcome: entry.outcome,
    }).then((didAnnounce) => {
      finalizeSubagentCleanup(evt.runId, entry.cleanup, didAnnounce);
    });
  });
}

function finalizeSubagentCleanup(runId: string, cleanup: "delete" | "keep", didAnnounce: boolean) {
  const entry = subagentRuns.get(runId);
  if (!entry) return;
  if (cleanup === "delete") {
    subagentRuns.delete(runId);
    persistSubagentRuns();
    return;
  }
  if (!didAnnounce) {
    // Allow retry on the next wake if the announce failed.
    entry.cleanupHandled = false;
    persistSubagentRuns();
    return;
  }
  entry.cleanupCompletedAt = Date.now();
  persistSubagentRuns();
}

function beginSubagentCleanup(runId: string) {
  const entry = subagentRuns.get(runId);
  if (!entry) return false;
  if (entry.cleanupCompletedAt) return false;
  if (entry.cleanupHandled) return false;
  entry.cleanupHandled = true;
  persistSubagentRuns();
  return true;
}

export function registerSubagentRun(params: {
  runId: string;
  childSessionKey: string;
  requesterSessionKey: string;
  requesterOrigin?: DeliveryContext;
  requesterDisplayKey: string;
  task: string;
  cleanup: "delete" | "keep";
  label?: string;
  runTimeoutSeconds?: number;
}) {
  const now = Date.now();
  const cfg = loadConfig();
  const archiveAfterMs = resolveArchiveAfterMs(cfg);
  const archiveAtMs = archiveAfterMs ? now + archiveAfterMs : undefined;
  const waitTimeoutMs = resolveSubagentWaitTimeoutMs(cfg, params.runTimeoutSeconds);
  const requesterOrigin = normalizeDeliveryContext(params.requesterOrigin);
  subagentRuns.set(params.runId, {
    runId: params.runId,
    childSessionKey: params.childSessionKey,
    requesterSessionKey: params.requesterSessionKey,
    requesterOrigin,
    requesterDisplayKey: params.requesterDisplayKey,
    task: params.task,
    cleanup: params.cleanup,
    label: params.label,
    createdAt: now,
    startedAt: now,
    archiveAtMs,
    cleanupHandled: false,
  });
  ensureListener();
  persistSubagentRuns();
  if (archiveAfterMs) startSweeper();
  if (resolveProgressCheckIntervalMs(cfg) > 0) startProgressChecker();
  // Wait for subagent completion via gateway RPC (cross-process).
  // The in-process lifecycle listener is a fallback for embedded runs.
  void waitForSubagentCompletion(params.runId, waitTimeoutMs);
}

async function waitForSubagentCompletion(runId: string, waitTimeoutMs: number) {
  try {
    const timeoutMs = Math.max(1, Math.floor(waitTimeoutMs));
    const wait = (await callGateway({
      method: "agent.wait",
      params: {
        runId,
        timeoutMs,
      },
      timeoutMs: timeoutMs + 10_000,
    })) as { status?: string; startedAt?: number; endedAt?: number; error?: string };
    if (wait?.status !== "ok" && wait?.status !== "error") return;
    const entry = subagentRuns.get(runId);
    if (!entry) return;
    let mutated = false;
    if (typeof wait.startedAt === "number") {
      entry.startedAt = wait.startedAt;
      mutated = true;
    }
    if (typeof wait.endedAt === "number") {
      entry.endedAt = wait.endedAt;
      mutated = true;
    }
    if (!entry.endedAt) {
      entry.endedAt = Date.now();
      mutated = true;
    }
    entry.outcome =
      wait.status === "error" ? { status: "error", error: wait.error } : { status: "ok" };
    mutated = true;
    if (mutated) persistSubagentRuns();
    if (!beginSubagentCleanup(runId)) return;
    const requesterOrigin = normalizeDeliveryContext(entry.requesterOrigin);
    void runSubagentAnnounceFlow({
      childSessionKey: entry.childSessionKey,
      childRunId: entry.runId,
      requesterSessionKey: entry.requesterSessionKey,
      requesterOrigin,
      requesterDisplayKey: entry.requesterDisplayKey,
      task: entry.task,
      timeoutMs: 30_000,
      cleanup: entry.cleanup,
      waitForCompletion: false,
      startedAt: entry.startedAt,
      endedAt: entry.endedAt,
      label: entry.label,
      outcome: entry.outcome,
    }).then((didAnnounce) => {
      finalizeSubagentCleanup(runId, entry.cleanup, didAnnounce);
    });
  } catch {
    // ignore
  }
}

export function resetSubagentRegistryForTests() {
  subagentRuns.clear();
  resumedRuns.clear();
  stopSweeper();
  stopProgressChecker();
  restoreAttempted = false;
  if (listenerStop) {
    listenerStop();
    listenerStop = null;
  }
  listenerStarted = false;
  pendingPersist = null;
  try {
    saveSubagentRegistryToDisk(subagentRuns);
  } catch {
    // ignore
  }
}

export function addSubagentRunForTests(entry: SubagentRunRecord) {
  subagentRuns.set(entry.runId, entry);
  persistSubagentRuns();
}

export function releaseSubagentRun(runId: string) {
  const didDelete = subagentRuns.delete(runId);
  if (didDelete) persistSubagentRuns();
  if (subagentRuns.size === 0) stopSweeper();
}

export function listSubagentRunsForRequester(requesterSessionKey: string): SubagentRunRecord[] {
  const key = requesterSessionKey.trim();
  if (!key) return [];
  return [...subagentRuns.values()].filter((entry) => entry.requesterSessionKey === key);
}

export function initSubagentRegistry() {
  restoreSubagentRunsOnce();
}
