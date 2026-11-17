import { proxyWithCookies } from "@/lib/api";

export const dynamic = "force-dynamic";

export async function GET(request: Request, context: { params: Promise<{ sessionId: string }> }) {
  const { sessionId } = await context.params;
  return proxyWithCookies(`/api/chat/sessions/${encodeURIComponent(sessionId)}`, request);
}

export async function PATCH(request: Request, context: { params: Promise<{ sessionId: string }> }) {
  const { sessionId } = await context.params;
  const body = await request.text();
  return proxyWithCookies(`/api/chat/sessions/${encodeURIComponent(sessionId)}`, request, {
    method: "PATCH",
    body,
  });
}

export async function DELETE(
  request: Request,
  context: { params: Promise<{ sessionId: string }> },
) {
  const { sessionId } = await context.params;
  return proxyWithCookies(`/api/chat/sessions/${encodeURIComponent(sessionId)}`, request, {
    method: "DELETE",
  });
}
