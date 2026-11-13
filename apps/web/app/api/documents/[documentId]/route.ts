import { proxyWithCookies } from "@/lib/api";

export const dynamic = "force-dynamic";

export async function DELETE(
  request: Request,
  context: { params: Promise<{ documentId: string }> },
) {
  const { documentId } = await context.params;
  return proxyWithCookies(`/api/documents/${encodeURIComponent(documentId)}`, request, {
    method: "DELETE",
  });
}

export async function PATCH(
  request: Request,
  context: { params: Promise<{ documentId: string }> },
) {
  const { documentId } = await context.params;
  const body = await request.text();
  return proxyWithCookies(`/api/documents/${encodeURIComponent(documentId)}`, request, {
    method: "PATCH",
    body,
  });
}
