/**
 * Regression tests for Clawbot log issues (CLAWBOT_ISSUES_AND_SOLUTIONS.md).
 * Verifies fixes don't break original flows.
 */
import { describe, expect, it, vi } from "vitest";

import { resolveGatewayOptions } from "./gateway.js";

describe("clawbot issues regression", () => {
  describe("gatewayUrl validation (cron/canvas/nodes failure fix)", () => {
    it("rejects placeholder user_gateway_url", () => {
      const opts = resolveGatewayOptions({ gatewayUrl: "user_gateway_url" });
      expect(opts.url).toBeUndefined();
    });

    it("rejects other non-URL strings", () => {
      expect(resolveGatewayOptions({ gatewayUrl: "invalid" }).url).toBeUndefined();
      expect(resolveGatewayOptions({ gatewayUrl: "http://example.com" }).url).toBeUndefined();
    });

    it("preserves valid ws:// URLs", () => {
      expect(resolveGatewayOptions({ gatewayUrl: "ws://127.0.0.1:18789" }).url).toBe(
        "ws://127.0.0.1:18789",
      );
    });

    it("preserves valid wss:// URLs with path", () => {
      expect(resolveGatewayOptions({ gatewayUrl: "wss://host:18789/path" }).url).toBe(
        "wss://host:18789/path",
      );
    });
  });

  describe("original flow: no gatewayUrl (config fallback)", () => {
    it("leaves url undefined when not provided", () => {
      const opts = resolveGatewayOptions({});
      expect(opts.url).toBeUndefined();
    });

    it("leaves url undefined when gatewayUrl is empty string", () => {
      const opts = resolveGatewayOptions({ gatewayUrl: "   " });
      expect(opts.url).toBeUndefined();
    });
  });
});
