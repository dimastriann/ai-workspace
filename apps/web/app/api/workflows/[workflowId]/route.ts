import { proxyWithCookies } from "@/lib/api";

export const dynamic = "force-dynamic";

export async function GET(request: Request, context: { params: Promise<{ workflowId: string }> }) {
  const { workflowId } = await context.params;
  return proxyWithCookies(`/api/workflows/${encodeURIComponent(workflowId)}`, request);
}

export async function PUT(request: Request, context: { params: Promise<{ workflowId: string }> }) {
  const { workflowId } = await context.params;
  const body = await request.text();
  return proxyWithCookies(`/api/workflows/${encodeURIComponent(workflowId)}`, request, {
    method: "PUT",
    body,
  });
}

export async function DELETE(
  request: Request,
  context: { params: Promise<{ workflowId: string }> },
) {
  const { workflowId } = await context.params;
  return proxyWithCookies(`/api/workflows/${encodeURIComponent(workflowId)}`, request, {
    method: "DELETE",
  });
}
