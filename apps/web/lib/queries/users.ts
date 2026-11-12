"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import type { Role, User } from "@/lib/types";

export const userKeys = {
  all: ["users"] as const,
};

async function fetchUsers(): Promise<User[]> {
  const response = await fetch("/api/users");
  if (!response.ok) {
    throw new Error("Failed to load users");
  }
  return (await response.json()) as User[];
}

export function useUsers() {
  return useQuery({ queryKey: userKeys.all, queryFn: fetchUsers });
}

export function useCreateUser() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (input: { email: string; password: string; role: Role }) => {
      const response = await fetch("/api/users", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(input),
      });
      if (!response.ok) {
        throw new Error("Failed to create user");
      }
      return (await response.json()) as User;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: userKeys.all });
    },
  });
}

export function useUpdateUser() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ id, ...changes }: { id: string; role?: Role; is_active?: boolean }) => {
      const response = await fetch(`/api/users/${id}`, {
        method: "PATCH",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(changes),
      });
      if (!response.ok) {
        throw new Error("Failed to update user");
      }
      return (await response.json()) as User;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: userKeys.all });
    },
  });
}
