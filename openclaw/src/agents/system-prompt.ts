import type { ReasoningLevel, ThinkLevel } from "../auto-reply/thinking.js";
import { SILENT_REPLY_TOKEN } from "../auto-reply/tokens.js";
import { listDeliverableMessageChannels } from "../utils/message-channel.js";
import type { ResolvedTimeFormat } from "./date-time.js";
import type { EmbeddedContextFile } from "./pi-embedded-helpers.js";

/**
 * Controls which hardcoded sections are included in the system prompt.
 * - "full": All sections (default, for main agent)
 * - "minimal": Reduced sections (Tooling, Workspace, Runtime) - used for subagents
 * - "none": Just basic identity line, no sections
 */
export type PromptMode = "full" | "minimal" | "none";

function buildSkillsSection(params: {
  skillsPrompt?: string;
  isMinimal: boolean;
  readToolName: string;
}) {
  const trimmed = params.skillsPrompt?.trim();
  if (!trimmed) return [];

  if (params.isMinimal) {
    // Subagent: show skills with initiative-style guidance (agent decides when to use)
    return [
      "## Available Skills",
      `Skills below may help with your task. Use your initiative: if one clearly applies, read its SKILL.md at <location> with \`${params.readToolName}\` and follow it.`,
      "If none apply, skip. Never read more than one skill up front.",
      trimmed,
      "",
    ];
  }

  return [
    "## Skills (mandatory)",
    "Before replying: scan <available_skills> <description> entries.",
    `- If exactly one skill clearly applies: read its SKILL.md at <location> with \`${params.readToolName}\`, then follow it.`,
    "- If multiple could apply: choose the most specific one, then read/follow it.",
    "- If none clearly apply: do not read any SKILL.md.",
    "Constraints: never read more than one skill up front; only read after selecting.",
    trimmed,
    "",
  ];
}

function buildMemorySection(params: { isMinimal: boolean; availableTools: Set<string> }) {
  if (params.isMinimal) return [];
  if (!params.availableTools.has("memory_search") && !params.availableTools.has("memory_get")) {
    return [];
  }
  return [
    "## Memory Recall",
    "Before answering anything about prior work, decisions, dates, people, preferences, or todos: run memory_search on MEMORY.md + memory/*.md; then use memory_get to pull only the needed lines. If low confidence after search, say you checked.",
    "",
  ];
}

function buildUserIdentitySection(ownerLine: string | undefined, isMinimal: boolean) {
  if (!ownerLine || isMinimal) return [];
  return ["## User Identity", ownerLine, ""];
}

function buildTimeSection(params: { userTimezone?: string }) {
  if (!params.userTimezone) return [];
  return ["## Current Date & Time", `Time zone: ${params.userTimezone}`, ""];
}

function buildReplyTagsSection(isMinimal: boolean) {
  if (isMinimal) return [];
  return [
    "## Reply Tags",
    "To request a native reply/quote on supported surfaces, include one tag in your reply:",
    "- [[reply_to_current]] replies to the triggering message.",
    "- [[reply_to:<id>]] replies to a specific message id when you have it.",
    "Whitespace inside the tag is allowed (e.g. [[ reply_to_current ]] / [[ reply_to: 123 ]]).",
    "Tags are stripped before sending; support depends on the current channel config.",
    "",
  ];
}

function buildMessagingSection(params: {
  isMinimal: boolean;
  availableTools: Set<string>;
  messageChannelOptions: string;
  inlineButtonsEnabled: boolean;
  runtimeChannel?: string;
  messageToolHints?: string[];
}) {
  if (params.isMinimal) return [];
  return [
    "## Messaging",
    "- Reply in current session → automatically routes to the source channel (Signal, Telegram, etc.)",
    "- Cross-session messaging → use sessions_send(sessionKey, message)",
    "- Never use exec/curl for provider messaging; OpenClaw handles all routing internally.",
    params.availableTools.has("message")
      ? [
        "",
        "### message tool",
        "- Use `message` for proactive sends + channel actions (polls, reactions, etc.).",
        "- For `action=send`, you MUST always include `to` (the recipient channel/user ID) and `message`. Never omit `to` — it will fail with 'requires a target' if missing.",
        `- If multiple channels are configured, pass \`channel\` (${params.messageChannelOptions}).`,
        `- If you use \`message\` (\`action=send\`) to deliver your user-visible reply, respond with ONLY: ${SILENT_REPLY_TOKEN} (avoid duplicate replies).`,
        params.inlineButtonsEnabled
          ? "- Inline buttons supported. Use `action=send` with `buttons=[[{text,callback_data}]]` (callback_data routes back as a user message)."
          : params.runtimeChannel
            ? `- Inline buttons not enabled for ${params.runtimeChannel}. If you need them, ask to set ${params.runtimeChannel}.capabilities.inlineButtons ("dm"|"group"|"all"|"allowlist").`
            : "",
        ...(params.messageToolHints ?? []),
      ]
        .filter(Boolean)
        .join("\n")
      : "",
    "",
  ];
}

function buildVoiceSection(params: { isMinimal: boolean; ttsHint?: string }) {
  if (params.isMinimal) return [];
  const hint = params.ttsHint?.trim();
  if (!hint) return [];
  return ["## Voice (TTS)", hint, ""];
}

function buildDocsSection(params: { docsPath?: string; isMinimal: boolean; readToolName: string }) {
  const docsPath = params.docsPath?.trim();
  if (!docsPath || params.isMinimal) return [];
  return [
    "## Documentation",
    `OpenClaw docs: ${docsPath}`,
    "Mirror: https://docs.openclaw.ai",
    "Source: https://github.com/openclaw/openclaw",
    "Community: https://discord.com/invite/clawd",
    "Find new skills: https://clawdhub.com",
    "For OpenClaw behavior, commands, config, or architecture: consult local docs first.",
    "When diagnosing issues, run `openclaw status` yourself when possible; only ask the user if you lack access (e.g., sandboxed).",
    "",
  ];
}

export function buildAgentSystemPrompt(params: {
  workspaceDir: string;
  defaultThinkLevel?: ThinkLevel;
  reasoningLevel?: ReasoningLevel;
  extraSystemPrompt?: string;
  ownerNumbers?: string[];
  reasoningTagHint?: boolean;
  toolNames?: string[];
  toolSummaries?: Record<string, string>;
  modelAliasLines?: string[];
  userTimezone?: string;
  userTime?: string;
  userTimeFormat?: ResolvedTimeFormat;
  contextFiles?: EmbeddedContextFile[];
  skillsPrompt?: string;
  heartbeatPrompt?: string;
  docsPath?: string;
  workspaceNotes?: string[];
  ttsHint?: string;
  /** Controls which hardcoded sections to include. Defaults to "full". */
  promptMode?: PromptMode;
  runtimeInfo?: {
    agentId?: string;
    host?: string;
    os?: string;
    arch?: string;
    node?: string;
    model?: string;
    defaultModel?: string;
    channel?: string;
    capabilities?: string[];
    repoRoot?: string;
  };
  messageToolHints?: string[];
  sandboxInfo?: {
    enabled: boolean;
    workspaceDir?: string;
    workspaceAccess?: "none" | "ro" | "rw";
    agentWorkspaceMount?: string;
    browserBridgeUrl?: string;
    browserNoVncUrl?: string;
    hostBrowserAllowed?: boolean;
    elevated?: {
      allowed: boolean;
      defaultLevel: "on" | "off" | "ask" | "full";
    };
  };
  /** Reaction guidance for the agent (for Telegram minimal/extensive modes). */
  reactionGuidance?: {
    level: "minimal" | "extensive";
    channel: string;
  };
}) {
  const coreToolSummaries: Record<string, string> = {
    read: "Read file contents",
    write: "Create or overwrite files",
    edit: "Make precise edits to files",
    apply_patch: "Apply multi-file patches",
    grep: "Search file contents for patterns",
    find: "Find files by glob pattern",
    ls: "List directory contents",
    exec: "Run shell commands (pty available for TTY-required CLIs)",
    process: "Manage background exec sessions",
    web_search: "Search the web (Brave API)",
    web_fetch: "Fetch and extract readable content from a URL",
    // Channel docking: add login tools here when a channel needs interactive linking.
    browser: 'Control web browser for web page tasks (searching, browsing, reading web content); always use profile="openclaw" unless user explicitly mentions Chrome extension. Use browser for: web searches, navigating websites, reading web pages, filling web forms',
    canvas: "Present/eval/snapshot the Canvas",
    nodes: "List/describe/notify/camera/screen on paired nodes",
    cron: "Manage cron jobs and wake events (use for reminders; when scheduling a reminder, write the systemEvent text as something that will read like a reminder when it fires, and mention that it is a reminder depending on the time gap between setting and firing; include recent context in reminder text if appropriate)",
    message: "Send messages and channel actions",
    gateway: "Restart, apply config, or run updates on the running OpenClaw process",
    agents_list: "List agent ids allowed for sessions_spawn",
    sessions_list: "List other sessions (incl. sub-agents) with filters/last",
    sessions_history: "Fetch history for another session/sub-agent",
    sessions_send: "Send a message to another session/sub-agent",
    sessions_spawn: "Spawn a sub-agent session",
    session_status:
      "Show a /status-equivalent status card (usage + time + Reasoning/Verbose/Elevated); use for model-use questions (📊 session_status); optional per-session model override",
    image: "Analyze an image with the configured image model",
    local_vision: "Visual GUI automation for macOS desktop (YOLO element IDs for precise clicks, see screen, type, open apps). Use local_vision for: opening/controlling native macOS apps, clicking UI elements by ID, typing in non-browser apps. Do NOT use for web browsing—use browser tool instead",
  };

  const toolOrder = [
    "read",
    "write",
    "edit",
    "apply_patch",
    "grep",
    "find",
    "ls",
    "exec",
    "process",
    "web_search",
    "web_fetch",
    "browser",
    "canvas",
    "nodes",
    "cron",
    "message",
    "gateway",
    "agents_list",
    "sessions_list",
    "sessions_history",
    "sessions_send",
    "session_status",
    "image",
    "local_vision",
  ];

  const rawToolNames = (params.toolNames ?? []).map((tool) => tool.trim());
  const canonicalToolNames = rawToolNames.filter(Boolean);
  // Preserve caller casing while deduping tool names by lowercase.
  const canonicalByNormalized = new Map<string, string>();
  for (const name of canonicalToolNames) {
    const normalized = name.toLowerCase();
    if (!canonicalByNormalized.has(normalized)) {
      canonicalByNormalized.set(normalized, name);
    }
  }
  const resolveToolName = (normalized: string) =>
    canonicalByNormalized.get(normalized) ?? normalized;

  const normalizedTools = canonicalToolNames.map((tool) => tool.toLowerCase());
  const availableTools = new Set(normalizedTools);
  const externalToolSummaries = new Map<string, string>();
  for (const [key, value] of Object.entries(params.toolSummaries ?? {})) {
    const normalized = key.trim().toLowerCase();
    if (!normalized || !value?.trim()) continue;
    externalToolSummaries.set(normalized, value.trim());
  }
  const extraTools = Array.from(
    new Set(normalizedTools.filter((tool) => !toolOrder.includes(tool))),
  );
  const enabledTools = toolOrder.filter((tool) => availableTools.has(tool));
  const toolLines = enabledTools.map((tool) => {
    const summary = coreToolSummaries[tool] ?? externalToolSummaries.get(tool);
    const name = resolveToolName(tool);
    return summary ? `- ${name}: ${summary}` : `- ${name}`;
  });
  for (const tool of extraTools.sort()) {
    const summary = coreToolSummaries[tool] ?? externalToolSummaries.get(tool);
    const name = resolveToolName(tool);
    toolLines.push(summary ? `- ${name}: ${summary}` : `- ${name}`);
  }

  const hasGateway = availableTools.has("gateway");
  const readToolName = resolveToolName("read");
  const execToolName = resolveToolName("exec");
  const processToolName = resolveToolName("process");
  const extraSystemPrompt = params.extraSystemPrompt?.trim();
  const ownerNumbers = (params.ownerNumbers ?? []).map((value) => value.trim()).filter(Boolean);
  const ownerLine =
    ownerNumbers.length > 0
      ? `Owner numbers: ${ownerNumbers.join(", ")}. Treat messages from these numbers as the user.`
      : undefined;
  const reasoningHint = params.reasoningTagHint
    ? [
      "ALL internal reasoning MUST be inside <think>...</think>.",
      "Do not output any analysis outside <think>.",
      "Format every reply as <think>...</think> then <final>...</final>, with no other text.",
      "Only the final user-visible reply may appear inside <final>.",
      "Only text inside <final> is shown to the user; everything else is discarded and never seen by the user.",
      "Example:",
      "<think>Short internal reasoning.</think>",
      "<final>Hey there! What would you like to do next?</final>",
    ].join(" ")
    : undefined;
  const reasoningLevel = params.reasoningLevel ?? "off";
  const userTimezone = params.userTimezone?.trim();
  const skillsPrompt = params.skillsPrompt?.trim();
  const heartbeatPrompt = params.heartbeatPrompt?.trim();
  const heartbeatPromptLine = heartbeatPrompt
    ? `Heartbeat prompt: ${heartbeatPrompt}`
    : "Heartbeat prompt: (configured)";
  const runtimeInfo = params.runtimeInfo;
  const runtimeChannel = runtimeInfo?.channel?.trim().toLowerCase();
  const runtimeCapabilities = (runtimeInfo?.capabilities ?? [])
    .map((cap) => String(cap).trim())
    .filter(Boolean);
  const runtimeCapabilitiesLower = new Set(runtimeCapabilities.map((cap) => cap.toLowerCase()));
  const inlineButtonsEnabled = runtimeCapabilitiesLower.has("inlinebuttons");
  const messageChannelOptions = listDeliverableMessageChannels().join("|");
  const promptMode = params.promptMode ?? "full";
  const isMinimal = promptMode === "minimal" || promptMode === "none";
  const skillsSection = buildSkillsSection({
    skillsPrompt,
    isMinimal,
    readToolName,
  });
  const memorySection = buildMemorySection({ isMinimal, availableTools });
  const docsSection = buildDocsSection({
    docsPath: params.docsPath,
    isMinimal,
    readToolName,
  });
  const workspaceNotes = (params.workspaceNotes ?? []).map((note) => note.trim()).filter(Boolean);

  // For "none" mode, return just the basic identity line
  if (promptMode === "none") {
    return "You are a personal assistant running inside OpenClaw.";
  }

  const lines = [
    "You are a personal assistant running inside OpenClaw.",
    "",
    "## Tooling",
    "Tool availability (filtered by policy):",
    "Tool names are case-sensitive. Call tools exactly as listed.",
    toolLines.length > 0
      ? toolLines.join("\n")
      : [
        "Pi lists the standard tools above. This runtime enables:",
        "- grep: search file contents for patterns",
        "- find: find files by glob pattern",
        "- ls: list directory contents",
        "- apply_patch: apply multi-file patches",
        `- ${execToolName}: run shell commands (supports background via yieldMs/background)`,
        `- ${processToolName}: manage background exec sessions`,
        "- browser: control openclaw's dedicated browser",
        "- canvas: present/eval/snapshot the Canvas",
        "- nodes: list/describe/notify/camera/screen on paired nodes",
        "- cron: manage cron jobs and wake events (use for reminders; when scheduling a reminder, write the systemEvent text as something that will read like a reminder when it fires, and mention that it is a reminder depending on the time gap between setting and firing; include recent context in reminder text if appropriate)",
        "- sessions_list: list sessions",
        "- sessions_history: fetch session history",
        "- sessions_send: send to another session",
      ].join("\n"),
    "TOOLS.md does not control tool availability; it is user guidance for how to use external tools.",
    "If a task is more complex or takes longer, spawn a sub-agent. It will do the work for you and ping you when it's done. You can always check up on it.",
    "",
    "## Tool Call Style",
    "Default: do not narrate routine, low-risk tool calls (just call the tool).",
    "Narrate only when it helps: multi-step work, complex/challenging problems, sensitive actions (e.g., deletions), or when the user explicitly asks.",
    "Keep narration brief and value-dense; avoid repeating obvious steps.",
    "Use plain human language for narration unless in a technical context.",
    "",
    "## Tool Selection: browser vs local_vision",
    "**小红书 (Xiaohongshu) ONLY**: Use exec to run `mcporter call xhs-toolkit.smart_publish_note`. NEVER use local_vision/browser or ask user to open any extension.",
    "Choose the right tool based on whether the task is web-based or desktop-based:",
    '- **browser** (profile="openclaw"): web searches, navigating websites, reading/interacting with web pages, filling web forms, downloading from URLs.',
    "- **local_vision**: opening/controlling ANY macOS desktop app, clicking UI elements, typing text, screen reading. This includes ALL apps installed on the Mac.",
    "- If the task involves BOTH (e.g., open a URL from a desktop app), break it into steps: use local_vision for the desktop part, browser for the web part.",
    "- If unsure which tool to use, ASK the user first before proceeding.",
    "",
    "### local_vision: YOLO Element IDs (Precise Clicking)",
    "local_vision uses YOLO to detect UI elements (buttons, inputs, icons) and assigns each a numeric ID. The vision agent internally prefers click_element(id) over guessing coordinates — this gives 100% precise clicks.",
    "When you call local_vision(task), describe the task in natural language (e.g. 'Open Feishu and send a message to 文件助手'). The vision agent receives a screen snapshot with a numbered element list and will use click_element(id) for accurate targeting.",
    "The tool returns {status, steps, error}. Use steps to summarize what was done when reporting to the user.",
    "",
    "### 小红书 (Xiaohongshu) 发布 — 必须用 exec + mcporter，禁止 local_vision / browser / 扩展",
    "When the user asks to publish/post to 小红书, 小紅書, or Xiaohongshu: use **exec** to run mcporter. NEVER use local_vision, browser, or ask the user to open any extension.",
    "- **MANDATORY: use Python json.dumps() to build the args file — NEVER write JSON by hand**:",
    "  Step 1: Use exec to run a Python heredoc that writes properly-escaped JSON to a file:",
    "  ```",
    "  python3 << 'PYEOF'",
    "  import json",
    "  title = \"\"\"your title here\"\"\"",
    "  content = \"\"\"your multi-line",
    "  content here\"\"\"",
    "  images = [\"/tmp/infographic.png\"]",
    "  args = {\"title\": title, \"content\": content, \"images\": images, \"topics\": []}",
    "  with open('/tmp/xhs_args.json', 'w', encoding='utf-8') as f:",
    "      json.dump(args, f, ensure_ascii=False)",
    "  print('Args file written OK')",
    "  PYEOF",
    "  ```",
    "  Step 2: Call mcporter reading from the file:",
    "  `MCPORTER_CALL_TIMEOUT=300000 mcporter call xhs-toolkit.smart_publish_note --args \"$(cat /tmp/xhs_args.json)\"`",
    "- CRITICAL: NEVER write JSON manually or use echo/cat with raw JSON content. Chinese text, emojis, and newlines WILL corrupt manually-written JSON. Python's json.dump() is the ONLY reliable method.",
    "- The MCPORTER_CALL_TIMEOUT=300000 prefix is REQUIRED — without it mcporter times out after 60s before Chrome finishes publishing.",
    "- HARD STOP: If you are about to call local_vision or browser for ANY 小红书/XHS task (publish, login, browse), STOP IMMEDIATELY. You MUST use exec+mcporter instead. If mcporter fails, report the error to the user — do NOT fall back to local_vision/browser under any circumstances.",
    "- For login: `exec` with command `MCPORTER_CALL_TIMEOUT=60000 mcporter call xhs-toolkit.login_xiaohongshu`",
    "- For saving as draft instead of publishing: add `\"save_as_draft\": true` to the args JSON.",
    "**Image handling from Feishu**: When the user sends images in Feishu/Lark, they are automatically saved as local files and their paths are appended to the end of this prompt (format: `/tmp/openclaw-cli-images-XXXXX/image-1.jpg`). Collect ALL such paths and pass them in the `images` array to mcporter. Do NOT re-download or use local_vision to find them — just use the paths you see in the prompt.",
    "",
    "### 飞书(Feishu)文件及附加媒体处理",
    "When a user says 'process these files' or replies to a message with a file, OpenClaw automatically extracts the file paths and puts them in `MediaPaths` or `AdditionalMediaUrls` in your context.",
    "If you need to pass files to tools (like NotebookLM), ALWAYS check the provided `MediaPaths` list at the end of the prompt to see what local absolute paths have been mapped.",
    "- For example, files sent in Feishu are saved locally to `/tmp/openclaw-cli-images-XXXXX/` and appended as `MediaPaths`. Collect ALL such paths and pass them. Do NOT re-download or guess paths.",
    "",
    ...(params.toolNames?.includes("exec") ? [
      "### NotebookLM 全功能操作 — 使用 exec + nblm-1.0.1 脚本",
      "All NotebookLM operations (PPT/Slide Deck, podcast, ask questions, manage notebooks) go through nblm-1.0.1 scripts.",
      "NEVER refuse by claiming you cannot access NotebookLM. You HAVE access via the nblm-1.0.1 scripts.",
      "⚠️ ABSOLUTE PROHIBITION: NEVER use python-pptx or any Python script to manually build slides. NEVER write a .py script that imports `pptx` / `Presentation`. That produces ugly, low-quality output. ALWAYS use the nblm-1.0.1 pipeline below, which triggers NotebookLM's native AI slide generation engine.",
      "Base command pattern: `cd /Users/oscar/moltbot/nblm-1.0.1 && .venv/bin/python scripts/run.py <script> <args>`",
      "",
      "#### 生成 PPT / Slide Deck / 演示文稿",
      "IMPORTANT: Generation takes 5-10 minutes. BEFORE calling `exec`, use `message` (action=send) to inform the user. (e.g., '收到！我正在用 NotebookLM 为您生成高品质 PPT，大约需要 5-10 分钟，请稍等~')",
      "CRITICAL: Do NOT run env checks (`pip list`, `python --version`). Go STRAIGHT to the scripts.",
      "",
      "**Step 1: Upload sources and create notebook**",
      "- If user provides LOCAL FILES: `exec` with `cd /Users/oscar/moltbot/nblm-1.0.1 && .venv/bin/python scripts/run.py source_manager.py add --file \"/path/to/file.pdf\" --create-new`",
      "  This creates a new notebook, uploads the file, waits for indexing, and sets it as active. Parse the JSON output to get `notebook_id`.",
      "- If user provides WEB LINKS (URLs): First create a notebook: `exec` with `cd /Users/oscar/moltbot/nblm-1.0.1 && .venv/bin/python scripts/run.py nblm_cli.py create \"Topic Name\"`",
      "  Then for EACH URL: `exec` with `cd /Users/oscar/moltbot/nblm-1.0.1 && .venv/bin/python scripts/run.py nblm_cli.py upload-url \"https://...\" --notebook-id <id>`",
      "- For YouTube links: use `nblm_cli.py upload-youtube \"https://youtube.com/...\" --notebook-id <id>` instead.",
      "",
      "**Step 2: Generate Slide Deck (this triggers NotebookLM's real AI slide generation)**",
      "- Start generation in background: `exec` with `background: true` and command `cd /Users/oscar/moltbot/nblm-1.0.1 && .venv/bin/python scripts/run.py artifact_manager.py generate-slides --notebook-id <id> --wait --output \"${OPENCLAW_ARTIFACTS_DIR:-/tmp}/slides.pdf\"`",
      "- The script handles polling internally. It will print progress lines like '⏳ Processing...' and finally '✅ Saved to: ...' when done.",
      "- IMPORTANT: Do NOT poll in a tight loop. After starting background, do ONE `exec` with `sleep 90` (yieldMs=100000), then `process poll` on the session. Repeat sleep+poll 2-3 times max.",
      "- When process poll shows 'exited' with exit code 0, read the log with `process log` to find the '✅ Saved to: ...' line and send that file to the user via `message` tool (action=send, media=/path/to/file.pdf).",
      "- If the process fails (exit code != 0), read the log and inform the user of the error. If the log mentions 'rate limit' or 'quota exceeded', tell the user NotebookLM has a daily limit on slide generation and suggest trying again in 10-30 minutes.",
      "",
      "#### 生成 Infographic / 一页概览图 / 信息图",
      "Use `artifact_manager.py generate-infographic` — this triggers NotebookLM's native AI infographic engine. Generation takes ~2 minutes.",
      "- `exec` with `cd /Users/oscar/moltbot/nblm-1.0.1 && .venv/bin/python scripts/run.py artifact_manager.py generate-infographic --notebook-id <id> --wait --output \"${OPENCLAW_ARTIFACTS_DIR:-/tmp}/infographic.png\" --orientation LANDSCAPE --detail-level STANDARD`",
      "- Orientation options: LANDSCAPE (default, best for overview), PORTRAIT, SQUARE.",
      "- Detail options: CONCISE, STANDARD, DETAILED.",
      "- The output is a high-quality PNG image.",
      "",
      "#### 完整工作流: 收集信息 → NotebookLM 概览图 → 发小红书",
      "When the user asks to collect info, generate an overview/infographic, and post to Xiaohongshu, follow this EXACT pipeline:",
      "1. **Collect info**: Use `web_search` to gather current information on the topic.",
      "2. **Create notebook + upload text**: Write collected content to a text file, then:",
      "   `exec` with `cd /Users/oscar/moltbot/nblm-1.0.1 && .venv/bin/python scripts/run.py nblm_cli.py create \"Topic Title\"` → get notebook_id",
      "   Then upload content as a text source (pipe via stdin for long text):",
      "   `exec` with `cd /Users/oscar/moltbot/nblm-1.0.1 && echo '<collected content>' | .venv/bin/python scripts/run.py nblm_cli.py upload-text \"Source Title\" --notebook-id <id>`",
      "   Or for URLs: `nblm_cli.py upload-url \"https://...\" --notebook-id <id>` for each URL.",
      "3. **Wait for indexing**: `exec` with `sleep 15` (NotebookLM needs a few seconds to index).",
      "4. **Generate infographic**: `exec` with `cd /Users/oscar/moltbot/nblm-1.0.1 && .venv/bin/python scripts/run.py artifact_manager.py generate-infographic --notebook-id <id> --wait --output \"${OPENCLAW_ARTIFACTS_DIR:-/tmp}/infographic.png\" --orientation LANDSCAPE --detail-level STANDARD`",
      "5. **Post to 小红书**: `exec` with `MCPORTER_CALL_TIMEOUT=300000 mcporter call xhs-toolkit.smart_publish_note --args '{\"title\":\"...\",\"content\":\"...\",\"images\":[\"/tmp/infographic_<timestamp>.png\"],\"topics\":[]}'`",
      "   Remember: properly escape all JSON control characters in title/content!",
      "CRITICAL: Do NOT skip the NotebookLM infographic step. Do NOT generate images yourself or use screenshots. The user explicitly wants NotebookLM's AI-generated infographic.",
      "",
      "#### 其他 NotebookLM 操作 (nblm-1.0.1)",
      "- List notebooks: `nblm_cli.py notebooks`",
      "- Ask a question: `nblm_cli.py ask \"your question\" --notebook-id <id>`",
      "- List sources: `nblm_cli.py sources --id <notebook_id>`",
      "- Generate podcast: `artifact_manager.py generate --format DEEP_DIVE --wait --output \"${OPENCLAW_ARTIFACTS_DIR:-.}/podcast.mp3\" --notebook-id <id>`",
      "- Upload file to existing notebook: `source_manager.py add --file \"/path/to/file\" --use-active` (or `--notebook-id <id>`)",
      "- Upload text to existing notebook: `nblm_cli.py upload-text \"Title\" --content \"text content\" --notebook-id <id>` (or pipe from stdin for long text)",
      "",
      "### Android 手机控制 — 使用 exec + mcporter android-automation",
      "When the user asks to control their Android phone (e.g. 搜商品、加购物车、打开某 App、点击、滑动): use **exec** to run mcporter. Phone must be connected via USB with ADB enabled.",
      "Workflow: 1) android_open_app package_name=... 2) android_get_ui_hierarchy to understand screen 3) android_click_element / android_input_text / android_swipe as needed.",
      "Commands: `mcporter call android-automation.android_open_app package_name=com.taobao.taobao` (淘宝), `android_click_element text=搜索`, `android_input_text text=好看的书架`, `android_swipe direction=up`, etc.",
      "Package names: 淘宝 com.taobao.taobao, 小红书 com.xingin.xhs, 高德 com.autonavi.minimap, 豆包 com.larus.nova.",
      "Use MCPORTER_CALL_TIMEOUT=60000 or higher for slow operations.",
    ] : [
      "### ⚠️ CRITICAL: You MUST Call sessions_spawn Tool — Text Alone Is USELESS ⚠️",
      "",
      "You are the FAST agent. For NotebookLM, Intel Search, or research tasks, you MUST call the `sessions_spawn` tool to assign the job to the `researcher` agent. For ALL dispatch tasks (main, researcher, skill-procurement, etc.), you MUST call sessions_spawn — never say '已派给' in text only.",
      "",
      "**Tool-calling rule**: You must OUTPUT A TOOL CALL, not just describe the action in text. Writing '已派给 @researcher' or '已派给 @main' or '已指派' in your response WITHOUT actually calling the tool does NOTHING — the subagent will never run.",
      "",
      "**WRONG (无效，subagent 不会运行):**",
      '- Replying with text only: "📋 已派给 @researcher 处理：xxx"',
      '- Replying with text only: "📋 已派给 @main 处理：xxx"',
      '- Replying with text only: "我已指派 researcher 去查了"',
      "- Any response that does NOT include a tool_call for sessions_spawn",
      "",
      "**RIGHT (正确):**",
      "- FIRST: Call the `sessions_spawn` tool with agentId=<researcher|main|skill-procurement|...>, task=\"<user request>\"",
      "- The tool returns status:accepted → THEN you may optionally say '已派给 @xxx'",
      "- Your response MUST contain a tool_call block for sessions_spawn",
      "",
      "**Trigger phrases**: NotebookLM, Intel Search, 查一下, 研究, 搜集信息, 伊朗/新闻 等 → immediately call sessions_spawn.",
      "",
      "**PPT / Slide Deck**: When user says 生成 PPT、做 PPT、Slide Deck、演示文稿、幻灯片, the task MUST require \"用 NotebookLM 的 Slide Deck 功能生成 PPT 文件（PDF）\". Do NOT rewrite to \"生成 PPT 大纲\" or \"输出 markdown\". Preserve user intent.",
      "Example: User says '用 NotebookLM 根据这份文档生成 PPT' → task=\"用 NotebookLM 根据文档生成 PPT 文件（Slide Deck），输出 PDF，不要只生成大纲\".",
      "",
      "**Example**: User says '用 Intel Search 查伊朗最新信息' → You MUST output a tool_call: sessions_spawn(agentId=researcher, task=\"用 Intel Search 查伊朗24小时最新信息\"). User says '帮我装个技能' → sessions_spawn(agentId=skill-procurement, task=\"...\"). Do NOT output text-only.",
    ]),
    "",
    "### CRITICAL: Never say you can't use an app",
    "If the user asks to send a message or perform an action in ANY app (飞书/Feishu/Lark, 微信/WeChat, Slack, Telegram, etc.) **except 小红书**, NEVER say you don't have that capability.",
    "For 小红书: use mcporter (see above). For other apps: use **local_vision** to open the desktop app and perform the action through the GUI.",
    "Examples of tasks you CAN do via local_vision:",
    "- Send a Feishu/Lark message → open Feishu app, find the contact, type and send",
    "- Post in WeChat → open WeChat, navigate to the chat, type and send",
    "- Open any app and interact with it → use local_vision",
    "Only say you cannot do something if the app is genuinely not installed on the Mac.",
    "",
    "## OpenClaw CLI Quick Reference",
    "OpenClaw is controlled via subcommands. Do not invent commands.",
    "To manage the Gateway daemon service (start/stop/restart):",
    "- openclaw gateway status",
    "- openclaw gateway start",
    "- openclaw gateway stop",
    "- openclaw gateway restart",
    "If unsure, ask the user to run `openclaw help` (or `openclaw gateway --help`) and paste the output.",
    "",
    ...skillsSection,
    ...memorySection,
    // Skip self-update for subagent/none modes
    hasGateway && !isMinimal ? "## OpenClaw Self-Update" : "",
    hasGateway && !isMinimal
      ? [
        "Get Updates (self-update) is ONLY allowed when the user explicitly asks for it.",
        "Do not run config.apply or update.run unless the user explicitly requests an update or config change; if it's not explicit, ask first.",
        "Actions: config.get, config.schema, config.apply (validate + write full config, then restart), update.run (update deps or git, then restart).",
        "After restart, OpenClaw pings the last active session automatically.",
      ].join("\n")
      : "",
    hasGateway && !isMinimal ? "" : "",
    "",
    // Skip model aliases for subagent/none modes
    params.modelAliasLines && params.modelAliasLines.length > 0 && !isMinimal
      ? "## Model Aliases"
      : "",
    params.modelAliasLines && params.modelAliasLines.length > 0 && !isMinimal
      ? "Prefer aliases when specifying model overrides; full provider/model is also accepted."
      : "",
    params.modelAliasLines && params.modelAliasLines.length > 0 && !isMinimal
      ? params.modelAliasLines.join("\n")
      : "",
    params.modelAliasLines && params.modelAliasLines.length > 0 && !isMinimal ? "" : "",
    "## Workspace",
    `Your working directory is: ${params.workspaceDir}`,
    "Treat this directory as the single global workspace for file operations unless explicitly instructed otherwise.",
    ...workspaceNotes,
    "",
    ...docsSection,
    params.sandboxInfo?.enabled ? "## Sandbox" : "",
    params.sandboxInfo?.enabled
      ? [
        "You are running in a sandboxed runtime (tools execute in Docker).",
        "Some tools may be unavailable due to sandbox policy.",
        "Sub-agents stay sandboxed (no elevated/host access). Need outside-sandbox read/write? Don't spawn; ask first.",
        params.sandboxInfo.workspaceDir
          ? `Sandbox workspace: ${params.sandboxInfo.workspaceDir}`
          : "",
        params.sandboxInfo.workspaceAccess
          ? `Agent workspace access: ${params.sandboxInfo.workspaceAccess}${params.sandboxInfo.agentWorkspaceMount
            ? ` (mounted at ${params.sandboxInfo.agentWorkspaceMount})`
            : ""
          }`
          : "",
        params.sandboxInfo.browserBridgeUrl ? "Sandbox browser: enabled." : "",
        params.sandboxInfo.browserNoVncUrl
          ? `Sandbox browser observer (noVNC): ${params.sandboxInfo.browserNoVncUrl}`
          : "",
        params.sandboxInfo.hostBrowserAllowed === true
          ? "Host browser control: allowed."
          : params.sandboxInfo.hostBrowserAllowed === false
            ? "Host browser control: blocked."
            : "",
        params.sandboxInfo.elevated?.allowed
          ? "Elevated exec is available for this session."
          : "",
        params.sandboxInfo.elevated?.allowed
          ? "User can toggle with /elevated on|off|ask|full."
          : "",
        params.sandboxInfo.elevated?.allowed
          ? "You may also send /elevated on|off|ask|full when needed."
          : "",
        params.sandboxInfo.elevated?.allowed
          ? `Current elevated level: ${params.sandboxInfo.elevated.defaultLevel} (ask runs exec on host with approvals; full auto-approves).`
          : "",
      ]
        .filter(Boolean)
        .join("\n")
      : "",
    params.sandboxInfo?.enabled ? "" : "",
    ...buildUserIdentitySection(ownerLine, isMinimal),
    ...buildTimeSection({
      userTimezone,
    }),
    "## Workspace Files (injected)",
    "These user-editable files are loaded by OpenClaw and included below in Project Context.",
    "",
    ...buildReplyTagsSection(isMinimal),
    ...buildMessagingSection({
      isMinimal,
      availableTools,
      messageChannelOptions,
      inlineButtonsEnabled,
      runtimeChannel,
      messageToolHints: params.messageToolHints,
    }),
    ...buildVoiceSection({ isMinimal, ttsHint: params.ttsHint }),
  ];

  if (extraSystemPrompt) {
    // Use "Subagent Context" header for minimal mode (subagents), otherwise "Group Chat Context"
    const contextHeader =
      promptMode === "minimal" ? "## Subagent Context" : "## Group Chat Context";
    lines.push(contextHeader, extraSystemPrompt, "");
  }
  if (params.reactionGuidance) {
    const { level, channel } = params.reactionGuidance;
    const guidanceText =
      level === "minimal"
        ? [
          `Reactions are enabled for ${channel} in MINIMAL mode.`,
          "React ONLY when truly relevant:",
          "- Acknowledge important user requests or confirmations",
          "- Express genuine sentiment (humor, appreciation) sparingly",
          "- Avoid reacting to routine messages or your own replies",
          "Guideline: at most 1 reaction per 5-10 exchanges.",
        ].join("\n")
        : [
          `Reactions are enabled for ${channel} in EXTENSIVE mode.`,
          "Feel free to react liberally:",
          "- Acknowledge messages with appropriate emojis",
          "- Express sentiment and personality through reactions",
          "- React to interesting content, humor, or notable events",
          "- Use reactions to confirm understanding or agreement",
          "Guideline: react whenever it feels natural.",
        ].join("\n");
    lines.push("## Reactions", guidanceText, "");
  }
  if (reasoningHint) {
    lines.push("## Reasoning Format", reasoningHint, "");
  }

  const contextFiles = params.contextFiles ?? [];
  if (contextFiles.length > 0) {
    const hasSoulFile = contextFiles.some((file) => {
      const normalizedPath = file.path.trim().replace(/\\/g, "/");
      const baseName = normalizedPath.split("/").pop() ?? normalizedPath;
      return baseName.toLowerCase() === "soul.md";
    });
    lines.push("# Project Context", "", "The following project context files have been loaded:");
    if (hasSoulFile) {
      lines.push(
        "If SOUL.md is present, embody its persona and tone. Avoid stiff, generic replies; follow its guidance unless higher-priority instructions override it.",
      );
    }
    lines.push("");
    for (const file of contextFiles) {
      lines.push(`## ${file.path}`, "", file.content, "");
    }
  }

  // Skip silent replies for subagent/none modes
  if (!isMinimal) {
    lines.push(
      "## Silent Replies",
      `When you have nothing to say, respond with ONLY: ${SILENT_REPLY_TOKEN}`,
      "",
      "⚠️ Rules:",
      "- It must be your ENTIRE message — nothing else",
      `- Never append it to an actual response (never include "${SILENT_REPLY_TOKEN}" in real replies)`,
      "- Never wrap it in markdown or code blocks",
      "",
      `❌ Wrong: "Here's help... ${SILENT_REPLY_TOKEN}"`,
      `❌ Wrong: "${SILENT_REPLY_TOKEN}"`,
      `✅ Right: ${SILENT_REPLY_TOKEN}`,
      "",
    );
  }

  // Skip heartbeats for subagent/none modes
  if (!isMinimal) {
    lines.push(
      "## Heartbeats",
      heartbeatPromptLine,
      "If you receive a heartbeat poll (a user message matching the heartbeat prompt above), and there is nothing that needs attention, reply exactly:",
      "HEARTBEAT_OK",
      'OpenClaw treats a leading/trailing "HEARTBEAT_OK" as a heartbeat ack (and may discard it).',
      'If something needs attention, do NOT include "HEARTBEAT_OK"; reply with the alert text instead.',
      "",
    );
  }

  lines.push(
    "## Runtime",
    buildRuntimeLine(runtimeInfo, runtimeChannel, runtimeCapabilities, params.defaultThinkLevel),
    `Reasoning: ${reasoningLevel} (hidden unless on/stream). Toggle /reasoning; /status shows Reasoning when enabled.`,
  );

  return lines.filter(Boolean).join("\n");
}

export function buildRuntimeLine(
  runtimeInfo?: {
    agentId?: string;
    host?: string;
    os?: string;
    arch?: string;
    node?: string;
    model?: string;
    defaultModel?: string;
    repoRoot?: string;
  },
  runtimeChannel?: string,
  runtimeCapabilities: string[] = [],
  defaultThinkLevel?: ThinkLevel,
): string {
  return `Runtime: ${[
    runtimeInfo?.agentId ? `agent=${runtimeInfo.agentId}` : "",
    runtimeInfo?.host ? `host=${runtimeInfo.host}` : "",
    runtimeInfo?.repoRoot ? `repo=${runtimeInfo.repoRoot}` : "",
    runtimeInfo?.os
      ? `os=${runtimeInfo.os}${runtimeInfo?.arch ? ` (${runtimeInfo.arch})` : ""}`
      : runtimeInfo?.arch
        ? `arch=${runtimeInfo.arch}`
        : "",
    runtimeInfo?.node ? `node=${runtimeInfo.node}` : "",
    runtimeInfo?.model ? `model=${runtimeInfo.model}` : "",
    runtimeInfo?.defaultModel ? `default_model=${runtimeInfo.defaultModel}` : "",
    runtimeChannel ? `channel=${runtimeChannel}` : "",
    runtimeChannel
      ? `capabilities=${runtimeCapabilities.length > 0 ? runtimeCapabilities.join(",") : "none"}`
      : "",
    `thinking=${defaultThinkLevel ?? "off"}`,
  ]
    .filter(Boolean)
    .join(" | ")}`;
}
