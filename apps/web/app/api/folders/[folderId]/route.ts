import { proxyWithCookies } from "@/lib/api";

export const dynamic = "force-dynamic";

export async function PATCH(request: Request, context: { params: Promise<{ folderId: string }> }) {
  const { folderId } = await context.params;
  const body = await request.text();
  return proxyWithCookies(`/api/folders/${encodeURIComponent(folderId)}`, request, {
    method: "PATCH",
    body,
  });
}

export async function DELETE(request: Request, context: { params: Promise<{ folderId: string }> }) {
  const { folderId } = await context.params;
  const search = new URL(request.url).search;
  return proxyWithCookies(`/api/folders/${encodeURIComponent(folderId)}${search}`, request, {
    method: "DELETE",
  });
}
