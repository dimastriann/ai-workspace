"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import type { Project } from "@/lib/types";

export const projectKeys = {
  byWorkspace: (workspaceId: string | null) => ["projects", workspaceId ?? ""] as const,
};

async function fetchProjects(workspaceId: string | null): Promise<Project[]> {
  if (!workspaceId) {
    return [];
  }
  const response = await fetch(`/api/projects?workspace_id=${encodeURIComponent(workspaceId)}`);
  if (!response.ok) {
    throw new Error("Failed to load projects");
  }
  return (await response.json()) as Project[];
}

export function useProjects(workspaceId: string | null) {
  return useQuery({
    queryKey: projectKeys.byWorkspace(workspaceId),
    queryFn: () => fetchProjects(workspaceId),
    enabled: Boolean(workspaceId),
  });
}

export function useCreateProject(workspaceId: string | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (input: {
      name: string;
      description?: string;
      instructions?: string;
      memory_mode?: "workspace" | "project";
    }) => {
      const response = await fetch("/api/projects", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          workspace_id: workspaceId,
          memory_mode: "workspace",
          ...input,
        }),
      });
      if (!response.ok) {
        throw new Error("Failed to create project");
      }
      return (await response.json()) as Project;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["projects", workspaceId ?? ""] });
    },
  });
}

export function useUpdateProject(workspaceId: string | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (input: {
      projectId: string;
      name?: string;
      description?: string;
      instructions?: string;
      memory_mode?: "workspace" | "project";
    }) => {
      const { projectId, ...body } = input;
      const response = await fetch(`/api/projects/${encodeURIComponent(projectId)}`, {
        method: "PATCH",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!response.ok) {
        throw new Error("Failed to update project");
      }
      return (await response.json()) as Project;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["projects", workspaceId ?? ""] });
    },
  });
}

export function useDeleteProject(workspaceId: string | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (projectId: string) => {
      const response = await fetch(`/api/projects/${encodeURIComponent(projectId)}`, {
        method: "DELETE",
      });
      if (!response.ok) {
        throw new Error("Failed to delete project");
      }
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["projects", workspaceId ?? ""] });
    },
  });
}
