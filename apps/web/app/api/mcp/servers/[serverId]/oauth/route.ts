import { proxyWithCookies } from "@/lib/api";

export const dynamic = "force-dynamic";

export async function POST(request: Request, context: { params: Promise<{ serverId: string }> }) {
  const { serverId } = await context.params;
  return proxyWithCookies(`/api/mcp/servers/${encodeURIComponent(serverId)}/oauth/start`, request, {
    method: "POST",
  });
}

export async function DELETE(request: Request, context: { params: Promise<{ serverId: string }> }) {
  const { serverId } = await context.params;
  return proxyWithCookies(`/api/mcp/servers/${encodeURIComponent(serverId)}/oauth`, request, {
    method: "DELETE",
  });
}
