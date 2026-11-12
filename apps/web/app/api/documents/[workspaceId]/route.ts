import { proxyWithCookies } from "@/lib/api";

export const dynamic = "force-dynamic";

export async function GET(request: Request, context: { params: Promise<{ workspaceId: string }> }) {
  const { workspaceId } = await context.params;
  return proxyWithCookies(`/api/documents/${encodeURIComponent(workspaceId)}`, request);
}
