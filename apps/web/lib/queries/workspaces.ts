"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import type { Workspace } from "@/lib/types";

export const workspaceKeys = {
  all: ["workspaces"] as const,
};

async function fetchWorkspaces(): Promise<Workspace[]> {
  const response = await fetch("/api/workspaces");
  if (!response.ok) {
    throw new Error("Failed to load workspaces");
  }
  return (await response.json()) as Workspace[];
}

export function useWorkspaces() {
  return useQuery({ queryKey: workspaceKeys.all, queryFn: fetchWorkspaces });
}

export function useCreateWorkspace() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (input: { name: string; description?: string }): Promise<Workspace> => {
      const response = await fetch("/api/workspaces", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ description: "", ...input }),
      });
      if (!response.ok) {
        throw new Error("Failed to create workspace");
      }
      return (await response.json()) as Workspace;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: workspaceKeys.all });
    },
  });
}
