import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { describe, expect, it } from "vitest";
import {
  getArtifactsDirForSession,
  isSubagentSessionKey,
  scanArtifactsDir,
} from "./artifacts.js";

describe("artifacts", () => {
  it("isSubagentSessionKey", () => {
    expect(isSubagentSessionKey("agent:main:subagent:abc-123")).toBe(true);
    expect(isSubagentSessionKey("agent:researcher:subagent:xyz")).toBe(true);
    expect(isSubagentSessionKey("agent:main:main")).toBe(false);
    expect(isSubagentSessionKey("main")).toBe(false);
    expect(isSubagentSessionKey(undefined)).toBe(false);
    expect(isSubagentSessionKey("")).toBe(false);
  });

  it("getArtifactsDirForSession", () => {
    const dir = getArtifactsDirForSession("agent:main:subagent:abc-123");
    expect(dir).toContain(".openclaw");
    expect(dir).toContain("artifacts");
    expect(dir).toContain("agent-main-subagent-abc-123");
    expect(getArtifactsDirForSession("main")).toBeNull();
    expect(getArtifactsDirForSession(undefined)).toBeNull();
  });

  it("scanArtifactsDir - empty", () => {
    const result = scanArtifactsDir("/nonexistent-path-xyz");
    expect(result.files).toEqual([]);
    expect(result.links).toEqual([]);
    expect(result.errors).toEqual([]);
  });

  it("scanArtifactsDir - with files and links", () => {
    const tmpDir = path.join(os.tmpdir(), `artifacts-test-${Date.now()}`);
    fs.mkdirSync(tmpDir, { recursive: true });
    try {
      fs.writeFileSync(path.join(tmpDir, "a.pdf"), "pdf", "utf-8");
      fs.writeFileSync(path.join(tmpDir, "b.png"), "png", "utf-8");
      fs.writeFileSync(
        path.join(tmpDir, "links.json"),
        JSON.stringify([
          { label: "Link1", url: "https://a.com" },
          { url: "https://b.com" },
        ]),
        "utf-8",
      );
      const result = scanArtifactsDir(tmpDir);
      expect(result.files).toHaveLength(2);
      expect(result.files.some((p) => p.endsWith("a.pdf"))).toBe(true);
      expect(result.files.some((p) => p.endsWith("b.png"))).toBe(true);
      expect(result.links).toEqual([
        { label: "Link1", url: "https://a.com" },
        { label: undefined, url: "https://b.com" },
      ]);
      expect(result.errors).toEqual([]);
    } finally {
      fs.rmSync(tmpDir, { recursive: true, force: true });
    }
  });
});
