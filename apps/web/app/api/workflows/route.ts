import { proxyWithCookies } from "@/lib/api";

export const dynamic = "force-dynamic";

export async function GET(request: Request) {
  const search = new URL(request.url).search;
  return proxyWithCookies(`/api/workflows${search}`, request);
}

export async function POST(request: Request) {
  const body = await request.text();
  return proxyWithCookies("/api/workflows", request, {
    method: "POST",
    body,
  });
}
