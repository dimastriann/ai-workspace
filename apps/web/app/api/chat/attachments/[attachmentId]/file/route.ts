import { proxyFile } from "@/lib/api";

export const dynamic = "force-dynamic";

export async function GET(
  request: Request,
  context: { params: Promise<{ attachmentId: string }> },
) {
  const { attachmentId } = await context.params;
  return proxyFile(`/api/chat/attachments/${encodeURIComponent(attachmentId)}/file`, request);
}
