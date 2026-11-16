import { proxyWithCookies } from "@/lib/api";

export const dynamic = "force-dynamic";

export async function POST(request: Request, context: { params: Promise<{ serverId: string }> }) {
  const { serverId } = await context.params;
  return proxyWithCookies(`/api/mcp/servers/${encodeURIComponent(serverId)}/test`, request, {
    method: "POST",
  });
}
