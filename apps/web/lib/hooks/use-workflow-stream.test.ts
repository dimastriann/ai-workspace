import { TextEncoder } from "node:util";
import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { useWorkflowStream } from "./use-workflow-stream";

function sseResponse(frames: object[]): Response {
  const encoder = new TextEncoder();
  const body = new ReadableStream<Uint8Array>({
    start(controller) {
      for (const frame of frames) {
        controller.enqueue(encoder.encode(`data: ${JSON.stringify(frame)}\n\n`));
      }
      controller.close();
    },
  });
  return { ok: true, body } as unknown as Response;
}

function failedResponse(): Response {
  return { ok: false, body: null } as unknown as Response;
}

describe("useWorkflowStream", () => {
  beforeEach(() => {
    vi.unstubAllGlobals();
  });

  it("builds steps from the run event stream", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        sseResponse([
          { event: "run_started", run_id: "run-1" },
          { event: "step_started", step: 0, instruction: "Do it", skill: null },
          { event: "token", step: 0, token: "Hello" },
          { event: "token", step: 0, token: " world" },
          {
            event: "tool",
            step: 0,
            tool: "search",
            status: "completed",
            output: "ok",
          },
          { event: "step_completed", step: 0, output: "Hello world" },
          { event: "done" },
        ]),
      ),
    );

    const { result } = renderHook(() => useWorkflowStream());
    await act(async () => {
      await result.current.send("wf-1", "input");
    });

    expect(result.current.status).toBe("completed");
    expect(result.current.runId).toBe("run-1");
    expect(result.current.steps).toHaveLength(1);
    expect(result.current.steps[0]).toMatchObject({
      index: 0,
      instruction: "Do it",
      status: "completed",
      output: "Hello world",
    });
    expect(result.current.steps[0].tools).toHaveLength(1);
    expect(result.current.steps[0].tools[0].tool).toBe("search");
  });

  it("marks the run and running steps as errored", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        sseResponse([
          { event: "step_started", step: 0, instruction: "Do it", skill: null },
          { event: "error", message: "LLM unavailable" },
        ]),
      ),
    );

    const { result } = renderHook(() => useWorkflowStream());
    await act(async () => {
      await result.current.send("wf-1", "input");
    });

    expect(result.current.status).toBe("error");
    expect(result.current.error).toBe("LLM unavailable");
    expect(result.current.steps[0].status).toBe("error");
  });

  it("surfaces a failed start request", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(failedResponse()));

    const { result } = renderHook(() => useWorkflowStream());
    await act(async () => {
      await result.current.send("wf-1", "input");
    });

    expect(result.current.status).toBe("error");
    expect(result.current.error).toBe("Workflow run failed to start");
  });
});
