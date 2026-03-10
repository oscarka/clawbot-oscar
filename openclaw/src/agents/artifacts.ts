/**
 * 方案 A：约定输出目录 - 完成物回报
 *
 * 目录: ~/.openclaw/artifacts/<任务ID>/
 * 环境变量: OPENCLAW_ARTIFACTS_DIR
 * 工具若检测到该变量，则将生成的文件写入该目录；链接写入 links.json
 */

import fs from "node:fs";
import os from "node:os";
import path from "node:path";

export const OPENCLAW_ARTIFACTS_ENV = "OPENCLAW_ARTIFACTS_DIR";
const ARTIFACTS_ROOT = path.join(
  process.env.HOME || os.homedir(),
  ".openclaw",
  "artifacts",
);

/** 判断 sessionKey 是否为 subagent（子任务） */
export function isSubagentSessionKey(sessionKey: string | undefined): boolean {
  if (!sessionKey || typeof sessionKey !== "string") return false;
  return sessionKey.includes(":subagent:");
}

/**
 * 为 session 解析 artifacts 目录路径。
 * 使用 sessionKey 的 sanitized 形式作为任务 ID（subagent 的 sessionKey 含唯一 UUID）。
 */
export function getArtifactsDirForSession(sessionKey: string | undefined): string | null {
  if (!sessionKey || !isSubagentSessionKey(sessionKey)) return null;
  const sanitized = sessionKey.replace(/[:/\\]/g, "-").replace(/\s+/g, "-");
  if (!sanitized) return null;
  return path.join(ARTIFACTS_ROOT, sanitized);
}

/**
 * 确保 artifacts 目录存在并返回路径；若 session 非 subagent 则返回 null。
 */
export function ensureArtifactsDirForSession(sessionKey: string | undefined): string | null {
  const dir = getArtifactsDirForSession(sessionKey);
  if (!dir) return null;
  try {
    fs.mkdirSync(dir, { recursive: true });
    return dir;
  } catch {
    return null;
  }
}

export type ArtifactLink = { label?: string; url: string };

export type ScanArtifactsResult = {
  files: string[];
  links: ArtifactLink[];
  errors: string[];
};

/**
 * 扫描约定目录，收集文件和 links.json 中的链接。
 */
export function scanArtifactsDir(artifactsDir: string): ScanArtifactsResult {
  const result: ScanArtifactsResult = { files: [], links: [], errors: [] };

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
            for (const item of parsed) {
              if (item && typeof item.url === "string") {
                result.links.push({
                  label: typeof item.label === "string" ? item.label : undefined,
                  url: item.url,
                });
              }
            }
          }
        } catch (e) {
          result.errors.push(`links.json parse error: ${(e as Error).message}`);
        }
      } else {
        result.files.push(fullPath);
      }
    }
  }

  return result;
}
