import { apiFetch } from "@/lib/api";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function POST(request: Request, context: { params: Promise<{ workflowId: string }> }) {
  const { workflowId } = await context.params;
  const body = await request.text();
  const cookie = request.headers.get("cookie");

  const upstream = await apiFetch(`/api/workflows/${encodeURIComponent(workflowId)}/runs`, {
    method: "POST",
    body,
    headers: cookie ? { cookie } : {},
  });

  if (!upstream.ok || !upstream.body) {
    return new Response("Workflow run failed to start", {
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
