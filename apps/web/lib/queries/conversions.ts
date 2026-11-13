"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import type { Conversion, ConversionFormat } from "@/lib/types";

export const conversionKeys = {
  byDocument: (documentId: string) => ["conversion", documentId] as const,
};

async function fetchConversion(documentId: string): Promise<Conversion> {
  const response = await fetch(`/api/documents/${documentId}/conversion`);
  if (response.status === 404) {
    throw new Error("not-found");
  }
  if (!response.ok) {
    throw new Error("Failed to load conversion");
  }
  return (await response.json()) as Conversion;
}

export function useConversion(documentId: string | null, enabled: boolean) {
  return useQuery({
    queryKey: conversionKeys.byDocument(documentId ?? ""),
    queryFn: () => fetchConversion(documentId as string),
    enabled: Boolean(documentId) && enabled,
    retry: false,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === "pending" || status === "running" ? 1500 : false;
    },
  });
}

export function useConvertDocument() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      documentId,
      includeImages,
      format = "markdown",
    }: {
      documentId: string;
      includeImages: boolean;
      format?: ConversionFormat;
    }) => {
      const response = await fetch(`/api/documents/${documentId}/convert`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ format, include_images: includeImages }),
      });
      if (!response.ok) {
        throw new Error("Failed to start conversion");
      }
      return (await response.json()) as Conversion;
    },
    onSuccess: (conversion) => {
      queryClient.setQueryData(conversionKeys.byDocument(conversion.document_id), conversion);
    },
  });
}
