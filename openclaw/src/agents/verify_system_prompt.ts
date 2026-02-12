
import { buildAgentSystemPrompt } from "./system-prompt.js";

async function main() {
    console.log("Generating System Prompt...");

    const prompt = buildAgentSystemPrompt({
        workspaceDir: "/Users/oscar/moltbot",
        toolNames: ["local_vision", "read", "exec"],
        // minimal params
    });

    if (prompt.includes("Visual GUI automation for macOS")) {
        console.log("✅ 'local_vision' description found in System Prompt!");
        console.log("--- Snippet ---");
        const lines = prompt.split("\n");
        const visionLine = lines.find(l => l.includes("local_vision"));
        console.log(visionLine);
    } else {
        console.error("❌ 'local_vision' description NOT found.");
        console.log(prompt); // Print full prompt for debugging
        process.exit(1);
    }
}

main().catch(console.error);
