"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

export const publicSettingsKeys = {
  all: ["public-settings"] as const,
};

async function fetchPublicSettings(): Promise<Record<string, boolean>> {
  const response = await fetch("/api/settings/public");
  if (!response.ok) {
    throw new Error("Failed to load feature flags");
  }
  return (await response.json()) as Record<string, boolean>;
}

export function usePublicSettings() {
  return useQuery({
    queryKey: publicSettingsKeys.all,
    queryFn: fetchPublicSettings,
  });
}

export function useUpdateSetting() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ key, value }: { key: string; value: boolean }) => {
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
      void queryClient.invalidateQueries({ queryKey: publicSettingsKeys.all });
    },
  });
}
