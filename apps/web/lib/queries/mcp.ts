"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import type { McpServer, McpStatus, McpTestResult } from "@/lib/types";

export const mcpKeys = {
  servers: ["mcp-servers"] as const,
  status: ["mcp-status"] as const,
};

async function fetchServers(): Promise<McpServer[]> {
  const response = await fetch("/api/mcp/servers");
  if (!response.ok) {
    throw new Error("Failed to load MCP servers");
  }
  return (await response.json()) as McpServer[];
}

export function useMcpServers() {
  return useQuery({ queryKey: mcpKeys.servers, queryFn: fetchServers });
}

function useServerMutation<TInput, TResult>(mutationFn: (input: TInput) => Promise<TResult>) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: mcpKeys.servers });
    },
  });
}

export interface McpServerInput {
  name: string;
  transport: "http" | "sse";
  url: string;
  headers?: Record<string, string> | null;
  enabled: boolean;
  timeout_seconds: number;
  disabled_tools?: string[];
}

export function useCreateMcpServer() {
  return useServerMutation(async (input: McpServerInput) => {
    const response = await fetch("/api/mcp/servers", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(input),
    });
    if (!response.ok) {
      throw new Error("Failed to create MCP server");
    }
    return (await response.json()) as McpServer;
  });
}

export function useUpdateMcpServer() {
  return useServerMutation(async (input: { serverId: string } & Partial<McpServerInput>) => {
    const { serverId, ...body } = input;
    const response = await fetch(`/api/mcp/servers/${encodeURIComponent(serverId)}`, {
      method: "PUT",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!response.ok) {
      throw new Error("Failed to update MCP server");
    }
    return (await response.json()) as McpServer;
  });
}

export function useDeleteMcpServer() {
  return useServerMutation(async (serverId: string) => {
    const response = await fetch(`/api/mcp/servers/${encodeURIComponent(serverId)}`, {
      method: "DELETE",
    });
    if (!response.ok) {
      throw new Error("Failed to delete MCP server");
    }
  });
}

export function useTestMcpServer() {
  return useServerMutation(async (serverId: string) => {
    const response = await fetch(`/api/mcp/servers/${encodeURIComponent(serverId)}/test`, {
      method: "POST",
    });
    if (!response.ok) {
      throw new Error("Failed to test MCP server");
    }
    return (await response.json()) as McpTestResult;
  });
}

async function fetchStatus(): Promise<McpStatus> {
  const response = await fetch("/api/mcp/status");
  if (!response.ok) {
    throw new Error("Failed to load MCP status");
  }
  return (await response.json()) as McpStatus;
}

export function useMcpStatus(enabled = true) {
  return useQuery({
    queryKey: mcpKeys.status,
    queryFn: fetchStatus,
    enabled,
  });
}

export function useReconnectMcpServer() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (serverId: string) => {
      const response = await fetch(`/api/mcp/servers/${encodeURIComponent(serverId)}/reconnect`, {
        method: "POST",
      });
      if (!response.ok) {
        throw new Error("Failed to reconnect MCP server");
      }
      return (await response.json()) as McpTestResult;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: mcpKeys.status });
      void queryClient.invalidateQueries({ queryKey: mcpKeys.servers });
    },
  });
}
