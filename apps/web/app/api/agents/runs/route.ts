import { apiFetch, proxyWithCookies } from "@/lib/api";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET(request: Request) {
  const url = new URL(request.url);
  const workspaceId = url.searchParams.get("workspace_id");
  const path = workspaceId
    ? `/api/agents/runs?workspace_id=${encodeURIComponent(workspaceId)}`
    : "/api/agents/runs";
  return proxyWithCookies(path, request);
}

export async function POST(request: Request) {
  const body = await request.text();
  const cookie = request.headers.get("cookie");

  const upstream = await apiFetch("/api/agents/runs", {
    method: "POST",
    body,
    headers: cookie ? { cookie } : {},
  });

  if (!upstream.ok || !upstream.body) {
    return new Response("Agent failed to start", {
      status: upstream.status || 502,
    });
  }

  return new Response(upstream.body, {
    status: 200,
    headers: {
      "content-type": "text/event-stream",
      "cache-control": "no-cache, no-transform",
      connection: "keep-alive",
      "x-accel-buffering": "no",
    },
  });
}
