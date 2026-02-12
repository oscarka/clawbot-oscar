
import { LocalVisionExecutor } from "./executor.js";
import { logger } from "../../utils/logger.js";

// Mock logger to avoid dependency issues during quick test
if (!logger) {
    (global as any).logger = {
        info: console.log,
        debug: console.log,
        error: console.error,
        warn: console.warn
    };
}

async function main() {
    console.log("🚀 Starting Integration Test: LocalVisionExecutor");

    const executor = new LocalVisionExecutor();

    // Test Case: Simple non-destructive task
    const task = "Open TextEdit and type 'OpenClaw Integration Test Successful'";

    console.log(`📋 Task: ${task}`);
    console.log("⏳ Execution started (this might take 10-20 seconds)...");

    try {
        const result = await executor.execute(task);
        console.log("\n✅ Result Received:");
        console.log(JSON.stringify(result, null, 2));

        if (result.status === "success") {
            console.log("🎉 Test PASSED");
            process.exit(0);
        } else {
            console.log("❌ Test FAILED (Status not success)");
            process.exit(1);
        }
    } catch (error) {
        console.error("\n❌ Test FAILED (Exception):", error);
        process.exit(1);
    }
}

main();
