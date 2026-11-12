import { proxyWithCookies } from "@/lib/api";

export const dynamic = "force-dynamic";

export async function GET(request: Request) {
  return proxyWithCookies("/api/users", request);
}

export async function POST(request: Request) {
  const body = await request.text();
  return proxyWithCookies("/api/users", request, { method: "POST", body });
}
