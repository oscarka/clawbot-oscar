
import { createOpenClawTools } from "./openclaw-tools.js";
import { loadConfig } from "../config/config.js";

async function main() {
    console.log("Checking available tools...");
    const config = loadConfig();
    const tools = createOpenClawTools({
        config: config
    });

    const visionTool = tools.find(t => t.name === "local_vision");

    if (visionTool) {
        console.log("✅ 'local_vision' tool is registered!");
        console.log("Description:", visionTool.description.trim().substring(0, 50) + "...");
    } else {
        console.error("❌ 'local_vision' tool NOT found.");
        process.exit(1);
    }
}

main().catch(console.error);
