import { proxyWithCookies } from "@/lib/api";

export const dynamic = "force-dynamic";

export async function PATCH(request: Request, context: { params: Promise<{ userId: string }> }) {
  const { userId } = await context.params;
  const body = await request.text();
  return proxyWithCookies(`/api/users/${encodeURIComponent(userId)}`, request, {
    method: "PATCH",
    body,
  });
}
