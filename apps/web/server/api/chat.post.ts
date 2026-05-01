/**
 * Nuxt Server Route — Chat Proxy (BFF)
 * 
 * Proxies the chat streaming request from the client to the FastAPI backend.
 * Handles the Server-Sent Events (SSE) stream.
 */

export default defineEventHandler(async (event) => {
  const config = useRuntimeConfig();
  const body = await readBody(event);

  // 1. Forward to FastAPI backend
  const response = await fetch(`${config.apiBaseUrl}/api/chat/stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    throw createError({
      statusCode: response.status,
      statusMessage: 'Failed to connect to AI engine',
    });
  }

  // 2. Stream the response back to the client
  // We set the correct headers for SSE
  setHeaders(event, {
    'Content-Type': 'text/event-stream',
    'Cache-Control': 'no-cache',
    'Connection': 'keep-alive',
  });

  // Proxy the readable stream
  return sendStream(event, response.body!);
});
