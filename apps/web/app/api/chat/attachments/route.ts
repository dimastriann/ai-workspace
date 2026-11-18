import { proxyFormWithCookies } from "@/lib/api";

export const dynamic = "force-dynamic";

export async function POST(request: Request) {
  const formData = await request.formData();
  return proxyFormWithCookies("/api/chat/attachments", request, formData);
}
