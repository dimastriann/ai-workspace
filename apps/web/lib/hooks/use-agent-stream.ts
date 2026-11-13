"use client";

import { useCallback, useState } from "react";

import type { AgentToolEvent } from "@/lib/types";

type AgentStatus = "idle" | "running" | "completed" | "error";

interface AgentEvent {
  event?: string;
  token?: string;
  tool?: string;
  status?: string;
  output?: string;
  message?: string;
  run_id?: string;
}

export function useAgentStream() {
  const [output, setOutput] = useState("");
  const [tools, setTools] = useState<AgentToolEvent[]>([]);
  const [status, setStatus] = useState<AgentStatus>("idle");
  const [runId, setRunId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const reset = useCallback(() => {
    setOutput("");
    setTools([]);
    setStatus("idle");
    setRunId(null);
    setError(null);
  }, []);

  const send = useCallback(
    async (instruction: string, workspaceId: string, skill: string | null) => {
      if (!instruction.trim() || !workspaceId) {
        return;
      }

      reset();
      setStatus("running");

      try {
        const response = await fetch("/api/agents/runs", {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({
            instruction,
            workspace_id: workspaceId,
            skill,
          }),
        });

        if (!response.ok || !response.body) {
          throw new Error("Agent run failed to start");
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
          const { value, done } = await reader.read();
          if (done) {
            break;
          }

          buffer += decoder.decode(value, { stream: true });
          const frames = buffer.split("\n\n");
          buffer = frames.pop() ?? "";

          for (const frame of frames) {
            const line = frame.trim();
            if (!line.startsWith("data:")) {
              continue;
            }
            const payload = line.slice(5).trim();
            if (!payload) {
              continue;
            }

            let event: AgentEvent;
            try {
              event = JSON.parse(payload) as AgentEvent;
            } catch {
              continue;
            }

            if (event.event === "run_started" && event.run_id) {
              setRunId(event.run_id);
            } else if (event.event === "token" && event.token) {
              const token = event.token;
              setOutput((previous) => previous + token);
            } else if (event.event === "tool" && event.tool) {
              setTools((previous) => [
                ...previous,
                {
                  id: crypto.randomUUID(),
                  tool: event.tool as string,
                  status: event.status ?? "completed",
                  output: event.output ?? "",
                },
              ]);
            } else if (event.event === "error") {
              setError(event.message ?? "Agent run failed");
              setStatus("error");
            } else if (event.event === "done") {
              setStatus("completed");
            }
          }
        }

        setStatus((current) => (current === "error" ? current : "completed"));
      } catch (caught) {
        setError(caught instanceof Error ? caught.message : "Agent run failed");
        setStatus("error");
      }
    },
    [reset],
  );

  return { output, tools, status, runId, error, send, reset };
}
