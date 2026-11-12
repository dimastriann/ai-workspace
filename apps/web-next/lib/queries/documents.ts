"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import type { DocumentRecord } from "@/lib/types";

export const documentKeys = {
  byWorkspace: (workspaceId: string) => ["documents", workspaceId] as const,
};

async function fetchDocuments(workspaceId: string): Promise<DocumentRecord[]> {
  const response = await fetch(`/api/documents/${workspaceId}`);
  if (!response.ok) {
    throw new Error("Failed to load documents");
  }
  return (await response.json()) as DocumentRecord[];
}

export function useDocuments(workspaceId: string | null) {
  return useQuery({
    queryKey: documentKeys.byWorkspace(workspaceId ?? ""),
    queryFn: () => fetchDocuments(workspaceId as string),
    enabled: Boolean(workspaceId),
  });
}

export function useUploadDocument(workspaceId: string | null) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (file: File) => {
      if (!workspaceId) {
        throw new Error("No workspace selected");
      }

      const formData = new FormData();
      formData.append("file", file);

      const response = await fetch(`/api/documents/upload/${workspaceId}`, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        throw new Error("Upload failed");
      }

      return response.json();
    },
    onSuccess: () => {
      if (workspaceId) {
        void queryClient.invalidateQueries({
          queryKey: documentKeys.byWorkspace(workspaceId),
        });
      }
    },
  });
}
