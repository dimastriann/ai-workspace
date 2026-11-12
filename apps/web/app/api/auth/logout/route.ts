import { proxyWithCookies } from "@/lib/api";

export const dynamic = "force-dynamic";

export async function POST(request: Request) {
  return proxyWithCookies("/api/auth/logout", request, { method: "POST" });
}
