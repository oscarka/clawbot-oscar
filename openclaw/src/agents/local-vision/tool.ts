import { Type } from "@sinclair/typebox";
import { LocalVisionExecutor } from "./executor.js";
import type { AnyAgentTool } from "../tools/common.js";
import { jsonResult } from "../tools/common.js";

const VISION_TOOL_NAME = "local_vision";

const LocalVisionToolSchema = Type.Object({
    task: Type.String({ description: "The natural language description of what to do on the screen." }),
    maxSteps: Type.Optional(Type.Number({ description: "Maximum number of steps to execute (default: 5)" })),
});

export const createLocalVisionTool = (): AnyAgentTool => {
    return {
        label: "Local Vision",
        name: VISION_TOOL_NAME,
        description: `Uses a local Vision Agent (YOLO + OCR) to perform GUI actions on the macOS desktop.
The agent detects UI elements with numeric IDs and prefers click_element(id) for 100% accurate clicks.
Use when the user asks to "click", "type", "open", or "see" something on the screen.

Example tasks:
- "Open Safari and search for cats"
- "Click the send button"
- "Type 'Hello' in the text box"
- "Open Feishu and send a message to someone"
- "Open WeChat and check new messages"

The tool returns a JSON report of the actions taken.`,
        parameters: LocalVisionToolSchema,
        execute: async (_toolCallId, args) => {
            const params = args as { task: string; maxSteps?: number };
            const executor = new LocalVisionExecutor();
            const result = await executor.execute(params.task, params.maxSteps);
            return jsonResult(result);
        },
    };
};
