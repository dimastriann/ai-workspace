"use client";

import { useCallback, useState } from "react";

type WorkflowStatus = "idle" | "running" | "completed" | "error";
type StepStatus = "pending" | "running" | "completed" | "error";

export interface WorkflowToolEvent {
  id: string;
  tool: string;
  status: string;
  output: string;
}

export interface WorkflowRunStep {
  index: number;
  instruction: string;
  skill: string | null;
  status: StepStatus;
  output: string;
  tools: WorkflowToolEvent[];
}

interface WorkflowEvent {
  event?: string;
  step?: number;
  total?: number;
  instruction?: string;
  skill?: string | null;
  token?: string;
  tool?: string;
  status?: string;
  output?: string;
  message?: string;
  run_id?: string;
}

export function useWorkflowStream() {
  const [steps, setSteps] = useState<WorkflowRunStep[]>([]);
  const [status, setStatus] = useState<WorkflowStatus>("idle");
  const [runId, setRunId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const reset = useCallback(() => {
    setSteps([]);
    setStatus("idle");
    setRunId(null);
    setError(null);
  }, []);

  const updateStep = useCallback(
    (index: number, update: (step: WorkflowRunStep) => WorkflowRunStep) => {
      setSteps((previous) => previous.map((step) => (step.index === index ? update(step) : step)));
    },
    [],
  );

  const send = useCallback(
    async (workflowId: string, input: string) => {
      reset();
      setStatus("running");

      try {
        const response = await fetch(`/api/workflows/${encodeURIComponent(workflowId)}/runs`, {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({ input }),
        });

        if (!response.ok || !response.body) {
          throw new Error("Workflow run failed to start");
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

            let event: WorkflowEvent;
            try {
              event = JSON.parse(payload) as WorkflowEvent;
            } catch {
              continue;
            }

            if (event.event === "run_started" && event.run_id) {
              setRunId(event.run_id);
            } else if (event.event === "step_started" && event.step !== undefined) {
              const stepIndex = event.step;
              setSteps((previous) => [
                ...previous.filter((step) => step.index !== stepIndex),
                {
                  index: stepIndex,
                  instruction: event.instruction ?? "",
                  skill: event.skill ?? null,
                  status: "running",
                  output: "",
                  tools: [],
                },
              ]);
            } else if (event.event === "token" && event.step !== undefined) {
              const token = event.token ?? "";
              updateStep(event.step, (step) => ({
                ...step,
                output: step.output + token,
              }));
            } else if (event.event === "tool" && event.step !== undefined) {
              const tool = event.tool ?? "tool";
              const toolStatus = event.status ?? "completed";
              const output = event.output ?? "";
              updateStep(event.step, (step) => ({
                ...step,
                tools: [
                  ...step.tools,
                  {
                    id: crypto.randomUUID(),
                    tool,
                    status: toolStatus,
                    output,
                  },
                ],
              }));
            } else if (event.event === "step_completed" && event.step !== undefined) {
              updateStep(event.step, (step) => ({
                ...step,
                status: "completed",
                output: event.output ?? step.output,
              }));
            } else if (event.event === "error") {
              setError(event.message ?? "Workflow run failed");
              setStatus("error");
              setSteps((previous) =>
                previous.map((step) =>
                  step.status === "running" ? { ...step, status: "error" } : step,
                ),
              );
            } else if (event.event === "done") {
              setStatus("completed");
            }
          }
        }

        setStatus((current) => (current === "error" ? current : "completed"));
      } catch (caught) {
        setError(caught instanceof Error ? caught.message : "Workflow run failed");
        setStatus("error");
      }
    },
    [reset, updateStep],
  );

  return { steps, status, runId, error, send, reset };
}
