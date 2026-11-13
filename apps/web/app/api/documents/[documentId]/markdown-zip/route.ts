import { proxyFile } from "@/lib/api";

export const dynamic = "force-dynamic";

export async function GET(request: Request, context: { params: Promise<{ documentId: string }> }) {
  const { documentId } = await context.params;
  return proxyFile(`/api/documents/${encodeURIComponent(documentId)}/markdown.zip`, request);
}
