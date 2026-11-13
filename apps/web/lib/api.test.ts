import { afterEach, describe, expect, it, vi } from "vitest";

import { proxyWithCookies } from "./api";

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("proxyWithCookies", () => {
  it("forwards a 204 response without a body", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(null, { status: 204 })));
    const request = new Request("http://localhost/api/documents/1", {
      method: "DELETE",
      headers: { cookie: "session=abc" },
    });

    const response = await proxyWithCookies("/api/documents/1", request, {
      method: "DELETE",
    });

    expect(response.status).toBe(204);
    expect(await response.text()).toBe("");
  });
});
