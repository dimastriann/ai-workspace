import { proxyJson } from "@/lib/api";

export const dynamic = "force-dynamic";

export async function GET(
  _request: Request,
  context: { params: Promise<{ workspaceId: string }> },
) {
  const { workspaceId } = await context.params;
  return proxyJson(`/api/documents/${encodeURIComponent(workspaceId)}`);
}
