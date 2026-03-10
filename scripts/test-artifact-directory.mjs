#!/usr/bin/env node
/**
 * 方案 A（约定输出目录）测试脚本
 *
 * 测试流程：
 * 1. 模拟「工具」往约定目录写文件 + links.json
 * 2. 模拟「回报流程」扫目录、收集完成物
 * 3. 验证边界情况：空目录、多文件、格式错误等
 *
 * 运行: node scripts/test-artifact-directory.mjs
 */

import fs from "node:fs";
import path from "node:path";
import os from "node:os";

// 测试时用临时目录，避免沙箱/权限问题；真实环境用 ~/.openclaw/artifacts/<任务ID>
const ARTIFACTS_ROOT =
  process.env.OPENCLAW_TEST_USE_REAL_PATH === "1"
    ? path.join(process.env.HOME || os.homedir(), ".openclaw", "artifacts")
    : path.join(os.tmpdir(), "openclaw-artifacts-test");
const ENV_VAR = "OPENCLAW_ARTIFACTS_DIR";

// ========== 模拟：工具写入约定目录 ==========

function simulateToolWritesArtifacts(artifactsDir, options = {}) {
  const { withFile = true, withLinks = true, badLinksJson = false } = options;
  fs.mkdirSync(artifactsDir, { recursive: true });

  if (withFile) {
    const pdfPath = path.join(artifactsDir, "test-slides.pdf");
    fs.writeFileSync(pdfPath, "%PDF-1.4 dummy content for test\n", "utf-8");
  }

  if (withLinks) {
    const linksPath = path.join(artifactsDir, "links.json");
    const content = badLinksJson
      ? "not valid json"
      : JSON.stringify([
          { label: "小红书笔记", url: "https://creator.xiaohongshu.com/publish/success/xxx" },
        ]);
    fs.writeFileSync(linksPath, content, "utf-8");
  }
}

// ========== 模拟：回报流程扫目录 ==========

function scanArtifactsDir(artifactsDir) {
  const result = { files: [], links: [], errors: [] };

  if (!fs.existsSync(artifactsDir)) {
    return result;
  }

  const entries = fs.readdirSync(artifactsDir, { withFileTypes: true });
  for (const ent of entries) {
    const fullPath = path.join(artifactsDir, ent.name);
    if (ent.isFile()) {
      if (ent.name === "links.json") {
        try {
          const raw = fs.readFileSync(fullPath, "utf-8");
          const parsed = JSON.parse(raw);
          if (Array.isArray(parsed)) {
            result.links.push(...parsed);
          }
        } catch (e) {
          result.errors.push(`links.json 解析失败: ${e.message}`);
        }
      } else {
        result.files.push(fullPath);
      }
    }
  }

  return result;
}

// ========== 测试用例 ==========

let passed = 0;
let failed = 0;

function ok(name, cond, msg) {
  if (cond) {
    console.log(`  ✅ ${name}`);
    passed++;
    return true;
  }
  console.log(`  ❌ ${name}: ${msg}`);
  failed++;
  return false;
}

function runTest(name, fn) {
  console.log(`\n--- ${name} ---`);
  fn();
}

function main() {
  console.log("方案 A 约定输出目录 - 测试\n");
  console.log("根目录:", ARTIFACTS_ROOT);
  console.log("环境变量:", ENV_VAR);

  const testRunId = `test-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
  const testDir = path.join(ARTIFACTS_ROOT, testRunId);

  try {
    // 用例 1：正常情况 - 有文件 + 有链接
    runTest("用例 1：有文件 + 有 links.json", () => {
      simulateToolWritesArtifacts(testDir, { withFile: true, withLinks: true });
      const r = scanArtifactsDir(testDir);
      ok("收集到文件", r.files.length >= 1, `实际: ${r.files.length}`);
      ok("收集到链接", r.links.length >= 1, `实际: ${r.links.length}`);
      ok("无错误", r.errors.length === 0, r.errors.join("; "));
    });

    // 用例 2：只有文件，无链接
    const dir2 = path.join(ARTIFACTS_ROOT, `${testRunId}-2`);
    runTest("用例 2：只有文件，无 links.json", () => {
      simulateToolWritesArtifacts(dir2, { withFile: true, withLinks: false });
      const r = scanArtifactsDir(dir2);
      ok("收集到文件", r.files.length >= 1, `实际: ${r.files.length}`);
      ok("链接为空", r.links.length === 0, `实际: ${r.links.length}`);
    });

    // 用例 3：空目录
    const dir3 = path.join(ARTIFACTS_ROOT, `${testRunId}-3`);
    runTest("用例 3：空目录", () => {
      fs.mkdirSync(dir3, { recursive: true });
      const r = scanArtifactsDir(dir3);
      ok("文件为空", r.files.length === 0, `实际: ${r.files.length}`);
      ok("链接为空", r.links.length === 0, `实际: ${r.links.length}`);
      ok("不报错", true, "");
    });

    // 用例 4：目录不存在
    runTest("用例 4：目录不存在", () => {
      const r = scanArtifactsDir(path.join(ARTIFACTS_ROOT, "nonexistent-xxx"));
      ok("返回空结果", r.files.length === 0 && r.links.length === 0, "");
      ok("不抛错", true, "");
    });

    // 用例 5：links.json 格式错误
    const dir5 = path.join(ARTIFACTS_ROOT, `${testRunId}-5`);
    runTest("用例 5：links.json 格式错误", () => {
      simulateToolWritesArtifacts(dir5, { withFile: true, withLinks: true, badLinksJson: true });
      const r = scanArtifactsDir(dir5);
      ok("仍收集到文件", r.files.length >= 1, `实际: ${r.files.length}`);
      ok("链接被忽略", r.links.length === 0, `实际: ${r.links.length}`);
      ok("错误被记录", r.errors.length >= 1, `实际: ${r.errors.length}`);
    });

    // 用例 6：多文件
    const dir6 = path.join(ARTIFACTS_ROOT, `${testRunId}-6`);
    runTest("用例 6：多文件", () => {
      fs.mkdirSync(dir6, { recursive: true });
      fs.writeFileSync(path.join(dir6, "a.pdf"), "a", "utf-8");
      fs.writeFileSync(path.join(dir6, "b.png"), "b", "utf-8");
      fs.writeFileSync(path.join(dir6, "links.json"), JSON.stringify([{ label: "L", url: "U" }]), "utf-8");
      const r = scanArtifactsDir(dir6);
      ok("收集到 2 个文件", r.files.length === 2, `实际: ${r.files.length}`);
      ok("收集到 1 个链接", r.links.length === 1, `实际: ${r.links.length}`);
    });

    // 用例 7：模拟工具读环境变量
    runTest("用例 7：环境变量约定", () => {
      const dir7 = path.join(ARTIFACTS_ROOT, `${testRunId}-7`);
      process.env[ENV_VAR] = dir7;
      const fromEnv = process.env[ENV_VAR];
      ok("环境变量可读", fromEnv === dir7, `实际: ${fromEnv}`);
      delete process.env[ENV_VAR];
    });
  } finally {
    // 清理测试目录
    for (const d of [
      testDir,
      path.join(ARTIFACTS_ROOT, `${testRunId}-2`),
      path.join(ARTIFACTS_ROOT, `${testRunId}-3`),
      path.join(ARTIFACTS_ROOT, `${testRunId}-5`),
      path.join(ARTIFACTS_ROOT, `${testRunId}-6`),
      path.join(ARTIFACTS_ROOT, `${testRunId}-7`),
    ]) {
      if (fs.existsSync(d)) {
        fs.rmSync(d, { recursive: true });
      }
    }
  }

  console.log("\n========== 结果 ==========");
  console.log(`通过: ${passed}, 失败: ${failed}`);
  process.exit(failed > 0 ? 1 : 0);
}

main();
