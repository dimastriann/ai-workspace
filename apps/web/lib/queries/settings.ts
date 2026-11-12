"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import type { SettingValue } from "@/lib/types";

export const settingsKeys = {
  all: ["settings"] as const,
};

async function fetchSettings(): Promise<Record<string, SettingValue>> {
  const response = await fetch("/api/settings");
  if (!response.ok) {
    throw new Error("Failed to load settings");
  }
  return (await response.json()) as Record<string, SettingValue>;
}

export function useSettings() {
  return useQuery({ queryKey: settingsKeys.all, queryFn: fetchSettings });
}

export function useUpdateSetting() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ key, value }: { key: string; value: SettingValue }) => {
      const response = await fetch(`/api/settings/${encodeURIComponent(key)}`, {
        method: "PUT",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ value }),
      });
      if (!response.ok) {
        throw new Error("Failed to update setting");
      }
      return response.json();
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: settingsKeys.all });
    },
  });
}
