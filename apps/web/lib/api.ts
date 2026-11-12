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

export async function proxyForm(path: string, formData: FormData): Promise<Response> {
  const response = await fetch(`${apiBaseUrl}${path}`, {
    method: "POST",
    body: formData,
    cache: "no-store",
  });
  const body = await response.text();

  return new Response(body, {
    status: response.status,
    headers: {
      "content-type": response.headers.get("content-type") ?? "application/json",
    },
  });
}

export async function proxyWithCookies(
  path: string,
  request: Request,
  init: RequestInit = {},
): Promise<Response> {
  const cookie = request.headers.get("cookie");
  const contentType = request.headers.get("content-type");
  const response = await fetch(`${apiBaseUrl}${path}`, {
    ...init,
    cache: "no-store",
    headers: {
      ...(contentType ? { "content-type": contentType } : {}),
      ...init.headers,
      ...(cookie ? { cookie } : {}),
    },
  });

  const body = await response.text();
  const headers = new Headers({
    "content-type": response.headers.get("content-type") ?? "application/json",
  });
  const setCookie = response.headers.get("set-cookie");
  if (setCookie) {
    headers.set("set-cookie", setCookie);
  }

  return new Response(body, { status: response.status, headers });
}
