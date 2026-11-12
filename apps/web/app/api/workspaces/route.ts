import { proxyJson } from "@/lib/api";

export const dynamic = "force-dynamic";

export async function GET() {
  return proxyJson("/api/workspaces/");
}

export async function POST(request: Request) {
  const body = await request.text();
  return proxyJson("/api/workspaces/", { method: "POST", body });
}
