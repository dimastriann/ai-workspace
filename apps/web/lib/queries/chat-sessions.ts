"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import type { ChatSessionSummary } from "@/lib/types";

export const chatSessionKeys = {
  byWorkspace: (workspaceId: string | null) => ["chat-sessions", workspaceId ?? ""] as const,
};

async function fetchSessions(workspaceId: string | null): Promise<ChatSessionSummary[]> {
  const query = workspaceId ? `?workspace_id=${encodeURIComponent(workspaceId)}` : "";
  const response = await fetch(`/api/chat/sessions${query}`);
  if (!response.ok) {
    throw new Error("Failed to load chat sessions");
  }
  return (await response.json()) as ChatSessionSummary[];
}

export function useChatSessions(workspaceId: string | null) {
  return useQuery({
    queryKey: chatSessionKeys.byWorkspace(workspaceId),
    queryFn: () => fetchSessions(workspaceId),
  });
}

export function useDeleteChatSession(workspaceId: string | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (sessionId: string) => {
      const response = await fetch(`/api/chat/sessions/${encodeURIComponent(sessionId)}`, {
        method: "DELETE",
      });
      if (!response.ok) {
        throw new Error("Failed to delete chat session");
      }
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: chatSessionKeys.byWorkspace(workspaceId),
      });
    },
  });
}
