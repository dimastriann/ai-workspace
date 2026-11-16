import { proxyWithCookies } from "@/lib/api";

export const dynamic = "force-dynamic";

export async function GET(request: Request, context: { params: Promise<{ serverId: string }> }) {
  const { serverId } = await context.params;
  return proxyWithCookies(`/api/mcp/servers/${encodeURIComponent(serverId)}`, request);
}

export async function PUT(request: Request, context: { params: Promise<{ serverId: string }> }) {
  const { serverId } = await context.params;
  const body = await request.text();
  return proxyWithCookies(`/api/mcp/servers/${encodeURIComponent(serverId)}`, request, {
    method: "PUT",
    body,
  });
}

export async function DELETE(request: Request, context: { params: Promise<{ serverId: string }> }) {
  const { serverId } = await context.params;
  return proxyWithCookies(`/api/mcp/servers/${encodeURIComponent(serverId)}`, request, {
    method: "DELETE",
  });
}
