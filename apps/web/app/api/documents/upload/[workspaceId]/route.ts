import { proxyForm } from "@/lib/api";

export const dynamic = "force-dynamic";

export async function POST(
  request: Request,
  context: { params: Promise<{ workspaceId: string }> },
) {
  const { workspaceId } = await context.params;
  const formData = await request.formData();
  return proxyForm(`/api/documents/upload/${encodeURIComponent(workspaceId)}`, formData);
}
