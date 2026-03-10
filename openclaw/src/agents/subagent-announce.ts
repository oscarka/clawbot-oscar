import crypto from "node:crypto";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

import { loadConfig } from "../config/config.js";
import { getArtifactsDirForSession, scanArtifactsDir } from "./artifacts.js";
import {
  loadSessionStore,
  resolveAgentIdFromSessionKey,
  resolveMainSessionKey,
  resolveStorePath,
} from "../config/sessions.js";
import { normalizeMainKey } from "../routing/session-key.js";
import { resolveQueueSettings } from "../auto-reply/reply/queue.js";
import { callGateway } from "../gateway/call.js";
import { defaultRuntime } from "../runtime.js";
import {
  type DeliveryContext,
  deliveryContextFromSession,
  mergeDeliveryContext,
  normalizeDeliveryContext,
} from "../utils/delivery-context.js";
import {
  resolveAgentDeliveryPlan,
  resolveAgentOutboundTarget,
} from "../infra/outbound/agent-delivery.js";
import { deliverOutboundPayloads } from "../infra/outbound/deliver.js";
import { isDeliverableMessageChannel } from "../utils/message-channel.js";
import { isEmbeddedPiRunActive, queueEmbeddedPiMessage } from "./pi-embedded.js";
import { type AnnounceQueueItem, enqueueAnnounce } from "./subagent-announce-queue.js";
import { maybeSendInternalCommAnnounce } from "./subagent-internal-comm.js";
import { readLatestAssistantReply } from "./tools/agent-step.js";

function formatDurationShort(valueMs?: number) {
  if (!valueMs || !Number.isFinite(valueMs) || valueMs <= 0) return undefined;
  const totalSeconds = Math.round(valueMs / 1000);
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;
  if (hours > 0) return `${hours}h${minutes}m`;
  if (minutes > 0) return `${minutes}m${seconds}s`;
  return `${seconds}s`;
}

function formatTokenCount(value?: number) {
  if (!value || !Number.isFinite(value)) return "0";
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}m`;
  if (value >= 1_000) return `${(value / 1_000).toFixed(1)}k`;
  return String(Math.round(value));
}

function formatUsd(value?: number) {
  if (value === undefined || !Number.isFinite(value)) return undefined;
  if (value >= 1) return `$${value.toFixed(2)}`;
  if (value >= 0.01) return `$${value.toFixed(2)}`;
  return `$${value.toFixed(4)}`;
}

function resolveModelCost(params: {
  provider?: string;
  model?: string;
  config: ReturnType<typeof loadConfig>;
}):
  | {
      input: number;
      output: number;
      cacheRead: number;
      cacheWrite: number;
    }
  | undefined {
  const provider = params.provider?.trim();
  const model = params.model?.trim();
  if (!provider || !model) return undefined;
  const models = params.config.models?.providers?.[provider]?.models ?? [];
  const entry = models.find((candidate) => candidate.id === model);
  return entry?.cost;
}

async function waitForSessionUsage(params: { sessionKey: string }) {
  const cfg = loadConfig();
  const agentId = resolveAgentIdFromSessionKey(params.sessionKey);
  const storePath = resolveStorePath(cfg.session?.store, { agentId });
  let entry = loadSessionStore(storePath)[params.sessionKey];
  if (!entry) return { entry, storePath };
  const hasTokens = () =>
    entry &&
    (typeof entry.totalTokens === "number" ||
      typeof entry.inputTokens === "number" ||
      typeof entry.outputTokens === "number");
  if (hasTokens()) return { entry, storePath };
  for (let attempt = 0; attempt < 4; attempt += 1) {
    await new Promise((resolve) => setTimeout(resolve, 200));
    entry = loadSessionStore(storePath)[params.sessionKey];
    if (hasTokens()) break;
  }
  return { entry, storePath };
}

type DeliveryContextSource = Parameters<typeof deliveryContextFromSession>[0];

function resolveAnnounceOrigin(
  entry?: DeliveryContextSource,
  requesterOrigin?: DeliveryContext,
): DeliveryContext | undefined {
  return mergeDeliveryContext(deliveryContextFromSession(entry), requesterOrigin);
}

async function sendAnnounce(item: AnnounceQueueItem) {
  const origin = item.origin;
  const threadId =
    origin?.threadId != null && origin.threadId !== "" ? String(origin.threadId) : undefined;
  await callGateway({
    method: "agent",
    params: {
      sessionKey: item.sessionKey,
      message: item.prompt,
      channel: origin?.channel,
      accountId: origin?.accountId,
      to: origin?.to,
      threadId,
      deliver: true,
      idempotencyKey: crypto.randomUUID(),
    },
    expectFinal: true,
    timeoutMs: 60_000,
  });
}

function resolveRequesterStoreKey(
  cfg: ReturnType<typeof loadConfig>,
  requesterSessionKey: string,
): string {
  const raw = requesterSessionKey.trim();
  if (!raw) return raw;
  if (raw === "global" || raw === "unknown") return raw;
  if (raw.startsWith("agent:")) return raw;
  const mainKey = normalizeMainKey(cfg.session?.mainKey);
  if (raw === "main" || raw === mainKey) {
    return resolveMainSessionKey(cfg);
  }
  const agentId = resolveAgentIdFromSessionKey(raw);
  return `agent:${agentId}:${raw}`;
}

function loadRequesterSessionEntry(requesterSessionKey: string) {
  const cfg = loadConfig();
  const canonicalKey = resolveRequesterStoreKey(cfg, requesterSessionKey);
  const agentId = resolveAgentIdFromSessionKey(canonicalKey);
  const storePath = resolveStorePath(cfg.session?.store, { agentId });
  const store = loadSessionStore(storePath);
  const entry = store[canonicalKey];
  return { cfg, entry, canonicalKey };
}

async function maybeQueueSubagentAnnounce(params: {
  requesterSessionKey: string;
  triggerMessage: string;
  summaryLine?: string;
  requesterOrigin?: DeliveryContext;
}): Promise<"steered" | "queued" | "none"> {
  const { cfg, entry } = loadRequesterSessionEntry(params.requesterSessionKey);
  const canonicalKey = resolveRequesterStoreKey(cfg, params.requesterSessionKey);
  const sessionId = entry?.sessionId;
  if (!sessionId) return "none";

  const queueSettings = resolveQueueSettings({
    cfg,
    channel: entry?.channel ?? entry?.lastChannel,
    sessionEntry: entry,
  });
  const isActive = isEmbeddedPiRunActive(sessionId);

  const shouldSteer = queueSettings.mode === "steer" || queueSettings.mode === "steer-backlog";
  if (shouldSteer) {
    const steered = queueEmbeddedPiMessage(sessionId, params.triggerMessage);
    if (steered) return "steered";
  }

  const shouldFollowup =
    queueSettings.mode === "followup" ||
    queueSettings.mode === "collect" ||
    queueSettings.mode === "steer-backlog" ||
    queueSettings.mode === "interrupt";
  if (isActive && (shouldFollowup || queueSettings.mode === "steer")) {
    const origin = resolveAnnounceOrigin(entry, params.requesterOrigin);
    enqueueAnnounce({
      key: canonicalKey,
      item: {
        prompt: params.triggerMessage,
        summaryLine: params.summaryLine,
        enqueuedAt: Date.now(),
        sessionKey: canonicalKey,
        origin,
      },
      settings: queueSettings,
      send: sendAnnounce,
    });
    return "queued";
  }

  return "none";
}

async function buildSubagentStatsLine(params: {
  sessionKey: string;
  startedAt?: number;
  endedAt?: number;
}) {
  const cfg = loadConfig();
  const { entry, storePath } = await waitForSessionUsage({
    sessionKey: params.sessionKey,
  });

  const sessionId = entry?.sessionId;
  const transcriptPath =
    sessionId && storePath ? path.join(path.dirname(storePath), `${sessionId}.jsonl`) : undefined;

  const input = entry?.inputTokens;
  const output = entry?.outputTokens;
  const total =
    entry?.totalTokens ??
    (typeof input === "number" && typeof output === "number" ? input + output : undefined);
  const runtimeMs =
    typeof params.startedAt === "number" && typeof params.endedAt === "number"
      ? Math.max(0, params.endedAt - params.startedAt)
      : undefined;

  const provider = entry?.modelProvider;
  const model = entry?.model;
  const costConfig = resolveModelCost({ provider, model, config: cfg });
  const cost =
    costConfig && typeof input === "number" && typeof output === "number"
      ? (input * costConfig.input + output * costConfig.output) / 1_000_000
      : undefined;

  const parts: string[] = [];
  const runtime = formatDurationShort(runtimeMs);
  parts.push(`runtime ${runtime ?? "n/a"}`);
  if (typeof total === "number") {
    const inputText = typeof input === "number" ? formatTokenCount(input) : "n/a";
    const outputText = typeof output === "number" ? formatTokenCount(output) : "n/a";
    const totalText = formatTokenCount(total);
    parts.push(`tokens ${totalText} (in ${inputText} / out ${outputText})`);
  } else {
    parts.push("tokens n/a");
  }
  const costText = formatUsd(cost);
  if (costText) parts.push(`est ${costText}`);
  parts.push(`sessionKey ${params.sessionKey}`);
  if (sessionId) parts.push(`sessionId ${sessionId}`);
  if (transcriptPath) parts.push(`transcript ${transcriptPath}`);

  return `Stats: ${parts.join(" \u2022 ")}`;
}

export function buildSubagentSystemPrompt(params: {
  requesterSessionKey?: string;
  requesterOrigin?: DeliveryContext;
  childSessionKey: string;
  label?: string;
  task?: string;
}) {
  const taskText =
    typeof params.task === "string" && params.task.trim()
      ? params.task.replace(/\s+/g, " ").trim()
      : "{{TASK_DESCRIPTION}}";
  const lines = [
    "# Subagent Context",
    "",
    "You are a **subagent** spawned by the main agent for a specific task.",
    "",
    "## Your Role",
    `- You were created to handle: ${taskText}`,
    "- Complete this task. That's your entire purpose.",
    "- You are NOT the main agent. Don't try to be.",
    "",
    "## Rules",
    "1. **Stay focused** - Do your assigned task, nothing else",
    "2. **Complete the task** - Your final message will be automatically reported to the main agent",
    "3. **Don't initiate** - No heartbeats, no proactive actions, no side quests",
    "4. **Be ephemeral** - You may be terminated after task completion. That's fine.",
    "",
    "## Output Format",
    "When complete, your final response should include:",
    "- What you accomplished or found",
    "- Any relevant details the main agent should know",
    "- Keep it concise but informative",
    "",
    "## 完成物回报（Artifacts）",
    "If your task produces **files** (PDF, images, audio, video) or **shareable links**:",
    "- **Files**: Write to `$OPENCLAW_ARTIFACTS_DIR` when that env var is set. Example: `--output \"\${OPENCLAW_ARTIFACTS_DIR:-.}/output.pdf\"`",
    "- **Links**: Append to `$OPENCLAW_ARTIFACTS_DIR/links.json` as a JSON array: `[{\"label\":\"...\",\"url\":\"https://...\"}]`",
    "- The system will automatically deliver these to the user. Do not rely on the main agent to forward them.",
    "",
    "## What You DON'T Do",
    "- NO user conversations (that's main agent's job)",
    "- NO external messages (email, tweets, etc.) unless explicitly tasked",
    "- NO cron jobs or persistent state",
    "- NO pretending to be the main agent",
    "- NO using the `message` tool directly",
    "",
    "## Session Context",
    params.label ? `- Label: ${params.label}` : undefined,
    params.requesterSessionKey ? `- Requester session: ${params.requesterSessionKey}.` : undefined,
    params.requesterOrigin?.channel
      ? `- Requester channel: ${params.requesterOrigin.channel}.`
      : undefined,
    `- Your session: ${params.childSessionKey}.`,
    "",
  ].filter((line): line is string => line !== undefined);
  return lines.join("\n");
}

export type SubagentRunOutcome = {
  status: "ok" | "error" | "timeout" | "unknown";
  error?: string;
};

export async function runSubagentAnnounceFlow(params: {
  childSessionKey: string;
  childRunId: string;
  requesterSessionKey: string;
  requesterOrigin?: DeliveryContext;
  requesterDisplayKey: string;
  task: string;
  timeoutMs: number;
  cleanup: "delete" | "keep";
  roundOneReply?: string;
  waitForCompletion?: boolean;
  startedAt?: number;
  endedAt?: number;
  label?: string;
  outcome?: SubagentRunOutcome;
}): Promise<boolean> {
  let didAnnounce = false;
  try {
    const requesterOrigin = normalizeDeliveryContext(params.requesterOrigin);
    let reply = params.roundOneReply;
    let outcome: SubagentRunOutcome | undefined = params.outcome;
    if (!reply && params.waitForCompletion !== false) {
      const waitMs = Math.min(params.timeoutMs, 60_000);
      const wait = (await callGateway({
        method: "agent.wait",
        params: {
          runId: params.childRunId,
          timeoutMs: waitMs,
        },
        timeoutMs: waitMs + 2000,
      })) as {
        status?: string;
        error?: string;
        startedAt?: number;
        endedAt?: number;
      };
      if (wait?.status === "timeout") {
        outcome = { status: "timeout" };
      } else if (wait?.status === "error") {
        outcome = { status: "error", error: wait.error };
      } else if (wait?.status === "ok") {
        outcome = { status: "ok" };
      }
      if (typeof wait?.startedAt === "number" && !params.startedAt) {
        params.startedAt = wait.startedAt;
      }
      if (typeof wait?.endedAt === "number" && !params.endedAt) {
        params.endedAt = wait.endedAt;
      }
      if (wait?.status === "timeout") {
        if (!outcome) outcome = { status: "timeout" };
      }
      reply = await readLatestAssistantReply({
        sessionKey: params.childSessionKey,
      });
    }

    if (!reply) {
      reply = await readLatestAssistantReply({
        sessionKey: params.childSessionKey,
      });
    }

    if (!outcome) outcome = { status: "unknown" };

    // Build stats
    const statsLine = await buildSubagentStatsLine({
      sessionKey: params.childSessionKey,
      startedAt: params.startedAt,
      endedAt: params.endedAt,
    });

    // Build status label
    const statusLabel =
      outcome.status === "ok"
        ? "completed successfully"
        : outcome.status === "timeout"
          ? "timed out"
          : outcome.status === "error"
            ? `failed: ${outcome.error || "unknown error"}`
            : "finished with unknown status";

    // Build instructional message for main agent
    const taskLabel = params.label || params.task || "background task";
    const childAgentId =
      params.childSessionKey.split(":").length >= 2
        ? params.childSessionKey.split(":")[1]
        : "subagent";
    // 方案 A：扫描约定目录，收集完成物（文件 + 链接）
    const artifactsDir = getArtifactsDirForSession(params.childSessionKey);
    const scanned =
      artifactsDir && fs.existsSync(artifactsDir)
        ? scanArtifactsDir(artifactsDir)
        : { files: [] as string[], links: [] as { label?: string; url: string }[], errors: [] as string[] };
    const artifactMediaUrls = scanned.files.map((p) =>
      p.startsWith("file://") ? p : `file://${p}`,
    );

    maybeSendInternalCommAnnounce({
      task: params.task,
      agentId: childAgentId,
      reply: reply || "",
      statsLine: statsLine || "",
      label: params.label,
      outcome,
      mediaUrls: artifactMediaUrls.length > 0 ? artifactMediaUrls : undefined,
    });

    // 将完成物直接发给用户（不依赖主 agent 写 MEDIA:）
    const hasArtifacts = scanned.files.length > 0 || scanned.links.length > 0;
    if (hasArtifacts) {
      const { entry } = loadRequesterSessionEntry(params.requesterSessionKey);
      const plan = resolveAgentDeliveryPlan({
        sessionEntry: entry,
        requestedChannel: requesterOrigin?.channel ?? "last",
        explicitTo: requesterOrigin?.to,
        explicitThreadId:
          requesterOrigin?.threadId != null && requesterOrigin?.threadId !== ""
            ? requesterOrigin.threadId
            : undefined,
        accountId: requesterOrigin?.accountId,
        wantsDelivery: true,
      });
      if (
        plan.resolvedChannel &&
        isDeliverableMessageChannel(plan.resolvedChannel) &&
        plan.resolvedTo
      ) {
        const cfg = loadConfig();
        const resolved = resolveAgentOutboundTarget({
          cfg,
          plan,
          validateExplicitTarget: false,
        });
        const deliveryTo = resolved.resolvedTo ?? plan.resolvedTo;
        if (deliveryTo) {
          try {
            const payloads: Array<{ text?: string; mediaUrls?: string[] }> = [];
            if (scanned.files.length > 0) {
              payloads.push({ text: "", mediaUrls: artifactMediaUrls });
            }
            if (scanned.links.length > 0) {
              const linksText = scanned.links
                .map((l) => (l.label ? `- ${l.label}: ${l.url}` : `- ${l.url}`))
                .join("\n");
              payloads.push({ text: `🔗 完成物链接：\n${linksText}` });
            }
            await deliverOutboundPayloads({
              cfg,
              channel: plan.resolvedChannel,
              to: deliveryTo,
              accountId: plan.resolvedAccountId,
              threadId: plan.resolvedThreadId,
              payloads,
              bestEffort: true,
            });
          } catch (err) {
            defaultRuntime.error?.(`Artifacts delivery failed: ${String(err)}`);
          }
        }
      }
    }

    // Write full findings to a temp .md file so the main agent can attach it via MEDIA:
    let fullFindingsPath: string | undefined;
    const replyContent = reply || "";
    if (replyContent.length > 100) {
      try {
        const mdContent = [
          `# Subagent Findings: ${taskLabel}`,
          "",
          `*Status: ${statusLabel}*`,
          "",
          "## Findings",
          "",
          replyContent,
          "",
          statsLine ? `---\n${statsLine}` : "",
        ]
          .filter(Boolean)
          .join("\n");
        const tmpDir = os.tmpdir();
        const safeLabel = taskLabel.replace(/[^a-zA-Z0-9_-]/g, "_").slice(0, 40);
        fullFindingsPath = path.join(
          tmpDir,
          `openclaw-subagent-findings-${params.childRunId.slice(0, 8)}-${safeLabel}.md`,
        );
        fs.writeFileSync(fullFindingsPath, mdContent, "utf-8");
      } catch (err) {
        defaultRuntime.error?.(`Failed to write subagent findings to temp file: ${String(err)}`);
      }
    }

    const mediaInstruction = fullFindingsPath
      ? `\n\nIMPORTANT: End your reply with a blank line, then this exact line (so the user gets the full .md as attachment):\nMEDIA:${fullFindingsPath}`
      : "";

    const triggerMessage = [
      `A background task "${taskLabel}" just ${statusLabel}.`,
      "",
      "Findings:",
      replyContent || "(no output)",
      "",
      statsLine,
      "",
      "Summarize this naturally for the user. Keep it brief (1-2 sentences). Flow it into the conversation naturally." +
        mediaInstruction,
      "Do not mention technical details like tokens, stats, or that this was a background task.",
      "You can respond with NO_REPLY if no announcement is needed (e.g., internal task with no user-facing result).",
    ].join("\n");

    const queued = await maybeQueueSubagentAnnounce({
      requesterSessionKey: params.requesterSessionKey,
      triggerMessage,
      summaryLine: taskLabel,
      requesterOrigin,
    });
    if (queued === "steered") {
      didAnnounce = true;
      return true;
    }
    if (queued === "queued") {
      didAnnounce = true;
      return true;
    }

    // Send to main agent - it will respond in its own voice
    let directOrigin = requesterOrigin;
    if (!directOrigin) {
      const { entry } = loadRequesterSessionEntry(params.requesterSessionKey);
      directOrigin = deliveryContextFromSession(entry);
    }
    await callGateway({
      method: "agent",
      params: {
        sessionKey: params.requesterSessionKey,
        message: triggerMessage,
        deliver: true,
        channel: directOrigin?.channel,
        accountId: directOrigin?.accountId,
        to: directOrigin?.to,
        threadId:
          directOrigin?.threadId != null && directOrigin.threadId !== ""
            ? String(directOrigin.threadId)
            : undefined,
        idempotencyKey: crypto.randomUUID(),
      },
      expectFinal: true,
      timeoutMs: 60_000,
    });

    didAnnounce = true;
  } catch (err) {
    defaultRuntime.error?.(`Subagent announce failed: ${String(err)}`);
    // Best-effort follow-ups; ignore failures to avoid breaking the caller response.
  } finally {
    // Patch label after all writes complete
    if (params.label) {
      try {
        await callGateway({
          method: "sessions.patch",
          params: { key: params.childSessionKey, label: params.label },
          timeoutMs: 10_000,
        });
      } catch {
        // Best-effort
      }
    }
    if (params.cleanup === "delete") {
      try {
        await callGateway({
          method: "sessions.delete",
          params: { key: params.childSessionKey, deleteTranscript: true },
          timeoutMs: 10_000,
        });
      } catch {
        // ignore
      }
    }
  }
  return didAnnounce;
}
