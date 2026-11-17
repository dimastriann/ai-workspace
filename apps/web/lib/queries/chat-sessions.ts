"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import type { ChatSessionSummary } from "@/lib/types";

export const chatSessionKeys = {
  byWorkspace: (workspaceId: string | null, query = "") =>
    ["chat-sessions", workspaceId ?? "", query] as const,
};

async function fetchSessions(
  workspaceId: string | null,
  query: string,
): Promise<ChatSessionSummary[]> {
  const params = new URLSearchParams();
  if (workspaceId) {
    params.set("workspace_id", workspaceId);
  }
  if (query.trim()) {
    params.set("q", query.trim());
  }
  const suffix = params.toString() ? `?${params.toString()}` : "";
  const response = await fetch(`/api/chat/sessions${suffix}`);
  if (!response.ok) {
    throw new Error("Failed to load chat sessions");
  }
  return (await response.json()) as ChatSessionSummary[];
}

export function useChatSessions(workspaceId: string | null, query = "") {
  return useQuery({
    queryKey: chatSessionKeys.byWorkspace(workspaceId, query),
    queryFn: () => fetchSessions(workspaceId, query),
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
        queryKey: ["chat-sessions", workspaceId ?? ""],
      });
    },
  });
}
