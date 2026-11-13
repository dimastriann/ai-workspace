"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import type { DocumentRecord, DocumentUploadResult } from "@/lib/types";

export const documentKeys = {
  byWorkspace: (workspaceId: string) => ["documents", workspaceId] as const,
};

async function fetchDocuments(workspaceId: string): Promise<DocumentRecord[]> {
  const response = await fetch(`/api/documents/workspace/${workspaceId}`);
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

export function useDeleteDocument(workspaceId: string | null) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (documentId: string) => {
      const response = await fetch(`/api/documents/${documentId}`, {
        method: "DELETE",
      });
      if (!response.ok) {
        throw new Error("Failed to delete document");
      }
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

export function useUploadDocument(workspaceId: string | null) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (input: { file: File; folderId?: string | null }) => {
      if (!workspaceId) {
        throw new Error("No workspace selected");
      }

      const formData = new FormData();
      formData.append("file", input.file);
      if (input.folderId) {
        formData.append("folder_id", input.folderId);
      }

      const response = await fetch(`/api/documents/upload/${workspaceId}`, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        throw new Error("Upload failed");
      }

      return (await response.json()) as DocumentUploadResult;
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

export function useMoveDocument(workspaceId: string | null) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (input: { documentId: string; folderId: string | null }) => {
      const response = await fetch(`/api/documents/${encodeURIComponent(input.documentId)}`, {
        method: "PATCH",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ folder_id: input.folderId }),
      });
      if (!response.ok) {
        throw new Error("Failed to move document");
      }
      return (await response.json()) as DocumentRecord;
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
