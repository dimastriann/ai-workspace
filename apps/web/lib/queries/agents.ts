"use client";

import { useQuery } from "@tanstack/react-query";

import type { AgentRunSummary, Skill } from "@/lib/types";

export const agentKeys = {
  skills: ["skills"] as const,
  runs: (workspaceId: string | null) => ["agent-runs", workspaceId] as const,
};

async function fetchSkills(): Promise<Skill[]> {
  const response = await fetch("/api/skills");
  if (!response.ok) {
    throw new Error("Failed to load skills");
  }
  return (await response.json()) as Skill[];
}

export function useSkills() {
  return useQuery({ queryKey: agentKeys.skills, queryFn: fetchSkills });
}

async function fetchRuns(workspaceId: string): Promise<AgentRunSummary[]> {
  const response = await fetch(`/api/agents/runs?workspace_id=${encodeURIComponent(workspaceId)}`);
  if (!response.ok) {
    throw new Error("Failed to load agent runs");
  }
  return (await response.json()) as AgentRunSummary[];
}

export function useAgentRuns(workspaceId: string | null) {
  return useQuery({
    queryKey: agentKeys.runs(workspaceId),
    queryFn: () => fetchRuns(workspaceId as string),
    enabled: Boolean(workspaceId),
  });
}
