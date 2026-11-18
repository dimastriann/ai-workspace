import { proxyWithCookies } from "@/lib/api";

export const dynamic = "force-dynamic";

export async function PATCH(request: Request, context: { params: Promise<{ messageId: string }> }) {
  const { messageId } = await context.params;
  const body = await request.text();
  return proxyWithCookies(
    `/api/chat/messages/${encodeURIComponent(messageId)}/alternative`,
    request,
    { method: "PATCH", body },
  );
}
