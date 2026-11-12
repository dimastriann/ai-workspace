import { proxyWithCookies } from "@/lib/api";

export const dynamic = "force-dynamic";

export async function PUT(request: Request, context: { params: Promise<{ key: string }> }) {
  const { key } = await context.params;
  const body = await request.text();
  return proxyWithCookies(`/api/settings/${encodeURIComponent(key)}`, request, {
    method: "PUT",
    body,
  });
}
