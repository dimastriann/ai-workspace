import { proxyWithCookies } from "@/lib/api";

export const dynamic = "force-dynamic";

export async function GET(request: Request) {
  const query = new URL(request.url).search;
  return proxyWithCookies(`/api/mcp/oauth/callback${query}`, request, { method: "GET" });
}
