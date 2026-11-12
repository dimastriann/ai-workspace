const apiBaseUrl = process.env.API_BASE_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

export async function apiFetch(path: string, init: RequestInit = {}): Promise<Response> {
  return fetch(`${apiBaseUrl}${path}`, {
    ...init,
    cache: "no-store",
    headers: {
      "content-type": "application/json",
      ...init.headers,
    },
  });
}

export async function apiJson<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await apiFetch(path, init);
  if (!response.ok) {
    throw new ApiError(response.status, `Upstream request failed: ${response.status}`);
  }
  return (await response.json()) as T;
}

export async function proxyJson(path: string, init: RequestInit = {}): Promise<Response> {
  const response = await apiFetch(path, init);
  const body = await response.text();

  return new Response(body, {
    status: response.status,
    headers: {
      "content-type": response.headers.get("content-type") ?? "application/json",
    },
  });
}
