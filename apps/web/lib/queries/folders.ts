"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import type { FolderRecord, FolderTree } from "@/lib/types";

export const folderKeys = {
  byWorkspace: (workspaceId: string) => ["folders", workspaceId] as const,
};

async function fetchFolders(workspaceId: string): Promise<FolderTree[]> {
  const response = await fetch(`/api/folders/workspace/${workspaceId}`);
  if (!response.ok) {
    throw new Error("Failed to load folders");
  }
  return (await response.json()) as FolderTree[];
}

export function useFolders(workspaceId: string | null) {
  return useQuery({
    queryKey: folderKeys.byWorkspace(workspaceId ?? ""),
    queryFn: () => fetchFolders(workspaceId as string),
    enabled: Boolean(workspaceId),
  });
}

function useFolderMutation<TInput, TResult>(
  workspaceId: string | null,
  mutationFn: (input: TInput) => Promise<TResult>,
) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn,
    onSuccess: () => {
      if (workspaceId) {
        void queryClient.invalidateQueries({
          queryKey: folderKeys.byWorkspace(workspaceId),
        });
      }
    },
  });
}

export function useCreateFolder(workspaceId: string | null) {
  return useFolderMutation(
    workspaceId,
    async (input: { name: string; parentId: string | null }) => {
      if (!workspaceId) {
        throw new Error("No workspace selected");
      }
      const response = await fetch("/api/folders", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          workspace_id: workspaceId,
          parent_id: input.parentId,
          name: input.name,
        }),
      });
      if (!response.ok) {
        throw new Error("Failed to create folder");
      }
      return (await response.json()) as FolderRecord;
    },
  );
}

export function useUpdateFolder(workspaceId: string | null) {
  return useFolderMutation(
    workspaceId,
    async (input: { folderId: string; name?: string; parentId?: string | null }) => {
      const body: { name?: string; parent_id?: string | null } = {};
      if (input.name !== undefined) {
        body.name = input.name;
      }
      if (input.parentId !== undefined) {
        body.parent_id = input.parentId;
      }
      const response = await fetch(`/api/folders/${encodeURIComponent(input.folderId)}`, {
        method: "PATCH",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!response.ok) {
        throw new Error("Failed to update folder");
      }
      return (await response.json()) as FolderRecord;
    },
  );
}

export function useDeleteFolder(workspaceId: string | null) {
  return useFolderMutation(
    workspaceId,
    async (input: { folderId: string; strategy: "reject" | "move_parent" }) => {
      const response = await fetch(
        `/api/folders/${encodeURIComponent(input.folderId)}?strategy=${input.strategy}`,
        { method: "DELETE" },
      );
      if (!response.ok) {
        throw new Error("Failed to delete folder");
      }
    },
  );
}
