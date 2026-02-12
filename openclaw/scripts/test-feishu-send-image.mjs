#!/usr/bin/env node
/**
 * Test script: send an image to Feishu group via the feishu-openclaw send logic.
 * Run: node scripts/test-feishu-send-image.mjs
 */
import { createRequire } from "node:module";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const require = createRequire(import.meta.url);

// Load config
const configPath = path.join(process.env.HOME || "", ".openclaw", "openclaw.json");
const cfg = JSON.parse(fs.readFileSync(configPath, "utf8"));
const feishu = cfg.channels?.feishu;
if (!feishu?.appId || !feishu?.appSecret) {
  console.error("Feishu appId/appSecret not configured in ~/.openclaw/openclaw.json");
  process.exit(1);
}

const chatId = "oc_07989c220c98a83e72c01eeb7f8ade54";

// Create a tiny test image (1x1 red pixel PNG)
const testPngBase64 =
  "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==";
const testImagePath = path.join(__dirname, "test-feishu-image.png");
fs.writeFileSync(testImagePath, Buffer.from(testPngBase64, "base64"));

// Dynamic import feishu plugin
const feishuExt = path.join(process.env.HOME || "", ".openclaw", "extensions", "feishu-openclaw");
const { sendMediaMessage } = await import(path.join(feishuExt, "dist/src/send.js"));
const Lark = await import(path.join(feishuExt, "node_modules/@larksuiteoapi/node-sdk/lib/index.js"));
const NS = Lark.default ?? Lark;

const client = new NS.Client({
  appId: feishu.appId,
  appSecret: feishu.appSecret,
  domain: NS.Domain.Feishu,
  appType: NS.AppType.SelfBuild,
});

console.log("Sending test image to Feishu group", chatId, "...");
const result = await sendMediaMessage(
  client,
  chatId,
  `file://${testImagePath}`,
  "测试图片 - 如果你看到这条消息，说明飞书发图已修复"
);
console.log("Result:", result);

fs.unlinkSync(testImagePath);
process.exit(result.ok ? 0 : 1);
