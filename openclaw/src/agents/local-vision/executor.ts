
import { spawn } from "child_process";
import path from "path";
import fs from "fs";
import { fileURLToPath } from "url";
import { loadConfig } from "../../config/config.js";
import { logger } from "../../utils/logger.js"; // Assuming a logger utility exists

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Resolve project root (works from both src/ and dist/)
function resolveProjectRoot(): string {
    let dir = __dirname;
    for (let i = 0; i < 10; i++) {
        if (fs.existsSync(path.join(dir, "package.json"))) return dir;
        dir = path.dirname(dir);
    }
    return path.join(__dirname, "..", "..", "..");
}

function resolveScriptPath(): string {
    // Try src/ first (Python files aren't compiled to dist/)
    const projectRoot = resolveProjectRoot();
    const srcPath = path.join(projectRoot, "src", "agents", "local-vision", "python", "vision_core.py");
    if (fs.existsSync(srcPath)) return srcPath;
    // Fallback: check relative to __dirname (in case files are copied to dist/)
    const distPath = path.join(__dirname, "python", "vision_core.py");
    if (fs.existsSync(distPath)) return distPath;
    throw new Error(`vision_core.py not found. Checked:\n  ${srcPath}\n  ${distPath}`);
}

/** Step action from vision agent (e.g. { action: "click_element", id: 5 }) */
export interface VisionStep {
    action: string;
    id?: number;
    app?: string;
    text?: string;
    key?: string;
    reason?: string;
}

export interface NonInteractiveVisionResult {
    status: "success" | "error" | "timeout";
    steps?: VisionStep[];
    /** YOLO-detected elements with id, label, confidence (if Python returns) */
    elements?: Array<{ id: number; label: string; confidence?: number }>;
    error?: string;
}

export class LocalVisionExecutor {
    private pythonPath: string;
    private scriptPath: string;

    constructor() {
        // Use python3.9 explicitly as it has the required dependencies (cv2, etc.)
        this.pythonPath = "/usr/local/bin/python3.9";
        this.scriptPath = resolveScriptPath();
    }

    public async execute(task: string, maxSteps?: number): Promise<NonInteractiveVisionResult> {
        console.log(`[DEBUG_TRACE] LocalVisionExecutor.execute called with task: "${task}"`);
        const config = loadConfig() as any;

        // Extract configured model preferences
        // Priority: Config -> Env -> Hardcoded Defaults
        const platform302Config = config?.ai?.models?.["302"] || {};
        const provider = "openai";
        const apiKey = platform302Config.apiKey || process.env.PLATFORM302_API_KEY || process.env.OPENAI_API_KEY;
        const baseUrl = platform302Config.baseUrl || "https://api.302.ai/v1";
        const model = platform302Config.defaultModel || "kimi-k2.5";

        return new Promise((resolve, reject) => {
            const args = [
                this.scriptPath,
                "--task", task,
                "--provider", provider,
                "--api-key", apiKey || "",
                "--base-url", baseUrl,
                "--model", model
            ];
            if (maxSteps != null && maxSteps > 0) {
                args.push("--max-steps", String(maxSteps));
            }

            logger.info(`[Vision] Spawning: ${this.pythonPath} ${args.join(" ")}`);

            const projectRoot = resolveProjectRoot();
            const child = spawn(this.pythonPath, args, {
                cwd: projectRoot,
                env: {
                    ...process.env,
                    PYTHONUNBUFFERED: "1"
                }
            });

            let stdoutData = "";
            let stderrData = "";

            child.stdout.on("data", (data) => {
                stdoutData += data.toString();
            });

            child.stderr.on("data", (data) => {
                const line = data.toString().trim();
                stderrData += line + "\n";
                // Forward Python logs to Node logger
                if (line) logger.debug(`[VisionPy] ${line}`);
            });

            child.on("close", (code) => {
                if (code !== 0) {
                    logger.error(`[Vision] Process exited with code ${code}`);
                    logger.error(`[Vision] Stderr: ${stderrData}`);
                    resolve({
                        status: "error",
                        error: `Process exited with code ${code}. Logs: ${stderrData}`
                    });
                    return;
                }

                try {
                    // Parse the LAST line that looks like JSON (vision_core prints final result on last line)
                    const lines = stdoutData.trim().split("\n").filter(Boolean);
                    let result: NonInteractiveVisionResult | null = null;
                    for (let i = lines.length - 1; i >= 0; i--) {
                        const line = lines[i].trim();
                        if (line.startsWith("{")) {
                            try {
                                result = JSON.parse(line) as NonInteractiveVisionResult;
                                break;
                            } catch {
                                continue;
                            }
                        }
                    }
                    if (result && typeof result.status === "string") {
                        resolve(result);
                    } else {
                        throw new Error("No valid JSON result found");
                    }
                } catch (e) {
                    logger.error(`[Vision] Failed to parse JSON output: ${stdoutData}`);
                    resolve({
                        status: "error",
                        error: `Invalid JSON output: ${e}`
                    });
                }
            });

            child.on("error", (err) => {
                reject(err);
            });
        });
    }
}
