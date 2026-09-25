import { describe, expect, test } from "bun:test";
import { buildHash, parseHash } from "./route";

describe("parseHash", () => {
  test("defaults to overview when empty", () => {
    expect(parseHash("").view).toBe("overview");
  });

  test("parses view and query params", () => {
    const route = parseHash("#/events?source=agent&since=100");
    expect(route.view).toBe("events");
    expect(route.params.get("source")).toBe("agent");
    expect(route.params.get("since")).toBe("100");
  });

  test("parses a view with no query string", () => {
    const route = parseHash("#/status");
    expect(route.view).toBe("status");
    expect(route.params.toString()).toBe("");
  });
});

describe("buildHash", () => {
  test("round-trips through parseHash", () => {
    const hash = buildHash("events", { source: "agent" });
    const route = parseHash(hash);
    expect(route.view).toBe("events");
    expect(route.params.get("source")).toBe("agent");
  });

  test("omits undefined/empty params", () => {
    expect(buildHash("ledger", { day: undefined, source: "" })).toBe("#/ledger");
  });
});
