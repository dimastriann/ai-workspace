import { proxyWithCookies } from "@/lib/api";

export const dynamic = "force-dynamic";

export async function GET(request: Request, context: { params: Promise<{ documentId: string }> }) {
  const { documentId } = await context.params;
  return proxyWithCookies(`/api/documents/${encodeURIComponent(documentId)}/conversion`, request);
}
