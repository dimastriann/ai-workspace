import { proxyStream } from "@/lib/api";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function POST(request: Request) {
  return proxyStream("/api/chat/regenerate", request);
}
