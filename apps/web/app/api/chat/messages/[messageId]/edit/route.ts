import { proxyStream } from "@/lib/api";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function POST(request: Request, context: { params: Promise<{ messageId: string }> }) {
  const { messageId } = await context.params;
  return proxyStream(`/api/chat/messages/${encodeURIComponent(messageId)}/edit`, request);
}
