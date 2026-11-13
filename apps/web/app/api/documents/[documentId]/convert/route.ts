import { proxyWithCookies } from "@/lib/api";

export const dynamic = "force-dynamic";

export async function POST(request: Request, context: { params: Promise<{ documentId: string }> }) {
  const { documentId } = await context.params;
  const body = await request.text();
  return proxyWithCookies(`/api/documents/${encodeURIComponent(documentId)}/convert`, request, {
    method: "POST",
    body,
  });
}
