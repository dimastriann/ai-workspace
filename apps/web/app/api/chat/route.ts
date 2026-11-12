import { apiFetch } from "@/lib/api";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function POST(request: Request) {
  const body = await request.text();
  const cookie = request.headers.get("cookie");

  const upstream = await apiFetch("/api/chat/stream", {
    method: "POST",
    body,
    headers: cookie ? { cookie } : {},
  });

  if (!upstream.ok || !upstream.body) {
    return new Response("Failed to connect to the AI engine", {
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
