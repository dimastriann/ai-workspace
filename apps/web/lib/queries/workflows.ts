"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import type { WorkflowDetail, WorkflowStepInput, WorkflowSummary } from "@/lib/types";

export const workflowKeys = {
  byWorkspace: (workspaceId: string) => ["workflows", workspaceId] as const,
  detail: (workflowId: string) => ["workflow", workflowId] as const,
};

async function fetchWorkflows(workspaceId: string): Promise<WorkflowSummary[]> {
  const response = await fetch(`/api/workflows?workspace_id=${encodeURIComponent(workspaceId)}`);
  if (!response.ok) {
    throw new Error("Failed to load workflows");
  }
  return (await response.json()) as WorkflowSummary[];
}

async function fetchWorkflow(workflowId: string): Promise<WorkflowDetail> {
  const response = await fetch(`/api/workflows/${workflowId}`);
  if (!response.ok) {
    throw new Error("Failed to load workflow");
  }
  return (await response.json()) as WorkflowDetail;
}

export function useWorkflows(workspaceId: string | null) {
  return useQuery({
    queryKey: workflowKeys.byWorkspace(workspaceId ?? ""),
    queryFn: () => fetchWorkflows(workspaceId as string),
    enabled: Boolean(workspaceId),
  });
}

export function useWorkflowDetail(workflowId: string | null, enabled = true) {
  return useQuery({
    queryKey: workflowKeys.detail(workflowId ?? ""),
    queryFn: () => fetchWorkflow(workflowId as string),
    enabled: Boolean(workflowId) && enabled,
  });
}

function useWorkflowMutation<TInput, TResult>(
  workspaceId: string | null,
  mutationFn: (input: TInput) => Promise<TResult>,
) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn,
    onSuccess: () => {
      if (workspaceId) {
        void queryClient.invalidateQueries({
          queryKey: workflowKeys.byWorkspace(workspaceId),
        });
      }
    },
  });
}

export function useCreateWorkflow(workspaceId: string | null) {
  return useWorkflowMutation(
    workspaceId,
    async (input: { name: string; description: string; steps: WorkflowStepInput[] }) => {
      if (!workspaceId) {
        throw new Error("No workspace selected");
      }
      const response = await fetch("/api/workflows", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          workspace_id: workspaceId,
          name: input.name,
          description: input.description,
          steps: input.steps,
        }),
      });
      if (!response.ok) {
        throw new Error("Failed to create workflow");
      }
      return (await response.json()) as WorkflowDetail;
    },
  );
}

export function useUpdateWorkflow(workspaceId: string | null) {
  return useWorkflowMutation(
    workspaceId,
    async (input: {
      workflowId: string;
      name: string;
      description: string;
      steps: WorkflowStepInput[];
    }) => {
      const response = await fetch(`/api/workflows/${encodeURIComponent(input.workflowId)}`, {
        method: "PUT",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          name: input.name,
          description: input.description,
          steps: input.steps,
        }),
      });
      if (!response.ok) {
        throw new Error("Failed to update workflow");
      }
      return (await response.json()) as WorkflowDetail;
    },
  );
}

export function useDeleteWorkflow(workspaceId: string | null) {
  return useWorkflowMutation(workspaceId, async (workflowId: string) => {
    const response = await fetch(`/api/workflows/${encodeURIComponent(workflowId)}`, {
      method: "DELETE",
    });
    if (!response.ok) {
      throw new Error("Failed to delete workflow");
    }
  });
}
