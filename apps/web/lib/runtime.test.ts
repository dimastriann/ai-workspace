import { describe, expect, it } from "vitest";

import { buildRuntimeUrl } from "./runtime";

describe("buildRuntimeUrl", () => {
  it("returns the base URL when no workspace is active", () => {
    expect(buildRuntimeUrl("http://localhost:8091")).toBe("http://localhost:8091");
    expect(buildRuntimeUrl("http://localhost:8091", null)).toBe("http://localhost:8091");
  });

  it("appends the workspace folder to the base URL", () => {
    expect(buildRuntimeUrl("http://localhost:8091", "da56-4fc4")).toBe(
      "http://localhost:8091?folder=%2Fhome%2Fcoder%2Fworkspace%2Fda56-4fc4",
    );
  });

  it("joins with & when the base URL already has a query", () => {
    expect(buildRuntimeUrl("http://localhost:8091?x=1", "abc")).toBe(
      "http://localhost:8091?x=1&folder=%2Fhome%2Fcoder%2Fworkspace%2Fabc",
    );
  });
});
