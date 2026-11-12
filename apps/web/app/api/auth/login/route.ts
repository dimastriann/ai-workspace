import { proxyWithCookies } from "@/lib/api";

export const dynamic = "force-dynamic";

export async function POST(request: Request) {
  const body = await request.text();
  return proxyWithCookies("/api/auth/login", request, { method: "POST", body });
}
