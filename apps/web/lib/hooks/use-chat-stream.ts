"use client";

import { useCallback, useRef, useState } from "react";

import type { ChatAttachment, ChatMessage, ChatRole, ChatSessionDetail, Source } from "@/lib/types";

interface StreamPayload {
  token?: string;
  session_id?: string;
  event?: string;
  message?: string;
  sources?: Source[];
}

interface StreamResult {
  content: string;
  sources: Source[];
}

function createMessage(role: ChatRole, content: string, sources: Source[] = []): ChatMessage {
  return { id: crypto.randomUUID(), role, content, sources };
}

export function useChatStream() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [streamingContent, setStreamingContent] = useState("");
  const [streamingSources, setStreamingSources] = useState<Source[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const readStream = useCallback(async (response: Response): Promise<StreamResult> => {
    if (!response.ok || !response.body) {
      throw new Error("Chat request failed");
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    let accumulated = "";
    let accumulatedSources: Source[] = [];
    let streamError: string | null = null;

    while (true) {
      const { value, done } = await reader.read();
      if (done) {
        break;
      }

      buffer += decoder.decode(value, { stream: true });
      const frames = buffer.split("\n\n");
      buffer = frames.pop() ?? "";

      for (const frame of frames) {
        const line = frame.trim();
        if (!line.startsWith("data:")) {
          continue;
        }
        const payload = line.slice(5).trim();
        if (!payload) {
          continue;
        }

        let data: StreamPayload;
        try {
          data = JSON.parse(payload) as StreamPayload;
        } catch {
          continue;
        }

        if (data.token) {
          accumulated += data.token;
          setStreamingContent(accumulated);
        } else if (data.sources) {
          accumulatedSources = data.sources;
          setStreamingSources(data.sources);
        } else if (data.session_id) {
          setSessionId(data.session_id);
        } else if (data.event === "error") {
          streamError = data.message ?? "Chat request failed";
        }
      }
    }

    if (streamError) {
      throw new Error(streamError);
    }
    return { content: accumulated, sources: accumulatedSources };
  }, []);

  const finishStream = useCallback((result: StreamResult) => {
    if (result.content) {
      setMessages((previous) => [
        ...previous,
        createMessage("assistant", result.content, result.sources),
      ]);
    }
    setStreamingContent("");
    setStreamingSources([]);
  }, []);

  const send = useCallback(
    async (
      content: string,
      workspaceId: string | null,
      disabledMcpTools: string[] = [],
      model: string | null = null,
      attachmentIds: string[] = [],
      attachments: ChatAttachment[] = [],
    ) => {
      if (!content.trim() || isStreaming) {
        return;
      }

      setError(null);
      setMessages((previous) => [...previous, { ...createMessage("user", content), attachments }]);
      setStreamingContent("");
      setStreamingSources([]);
      setIsStreaming(true);

      const controller = new AbortController();
      abortRef.current = controller;

      try {
        const response = await fetch("/api/chat", {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({
            message: content,
            session_id: sessionId,
            workspace_id: workspaceId,
            disabled_mcp_tools: disabledMcpTools,
            model,
            attachment_ids: attachmentIds,
          }),
          signal: controller.signal,
        });
        finishStream(await readStream(response));
      } catch (caught) {
        if (caught instanceof DOMException && caught.name === "AbortError") {
          return;
        }
        setError(
          caught instanceof Error
            ? caught.message
            : "Sorry, I encountered an error. Please try again.",
        );
      } finally {
        setIsStreaming(false);
        abortRef.current = null;
      }
    },
    [finishStream, isStreaming, readStream, sessionId],
  );

  const regenerate = useCallback(
    async (disabledMcpTools: string[] = []) => {
      if (!sessionId || isStreaming) {
        return;
      }

      setError(null);
      setMessages((previous) => {
        const next = [...previous];
        if (next.at(-1)?.role === "assistant") {
          next.pop();
        }
        return next;
      });
      setStreamingContent("");
      setStreamingSources([]);
      setIsStreaming(true);

      const controller = new AbortController();
      abortRef.current = controller;

      try {
        const response = await fetch("/api/chat/regenerate", {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({
            session_id: sessionId,
            disabled_mcp_tools: disabledMcpTools,
          }),
          signal: controller.signal,
        });
        finishStream(await readStream(response));
      } catch (caught) {
        if (caught instanceof DOMException && caught.name === "AbortError") {
          return;
        }
        setError(caught instanceof Error ? caught.message : "Could not regenerate.");
      } finally {
        setIsStreaming(false);
        abortRef.current = null;
      }
    },
    [finishStream, isStreaming, readStream, sessionId],
  );

  const editMessage = useCallback(
    async (messageId: string, content: string, disabledMcpTools: string[] = []) => {
      if (!sessionId || isStreaming || !content.trim()) {
        return;
      }

      setError(null);
      setMessages((previous) => {
        const index = previous.findIndex((message) => message.id === messageId);
        if (index < 0) {
          return previous;
        }
        return [...previous.slice(0, index), { ...previous[index], content: content.trim() }];
      });
      setStreamingContent("");
      setStreamingSources([]);
      setIsStreaming(true);

      const controller = new AbortController();
      abortRef.current = controller;

      try {
        const response = await fetch(`/api/chat/messages/${encodeURIComponent(messageId)}/edit`, {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({
            session_id: sessionId,
            message: content.trim(),
            disabled_mcp_tools: disabledMcpTools,
          }),
          signal: controller.signal,
        });
        finishStream(await readStream(response));
      } catch (caught) {
        if (caught instanceof DOMException && caught.name === "AbortError") {
          return;
        }
        setError(caught instanceof Error ? caught.message : "Could not edit message.");
      } finally {
        setIsStreaming(false);
        abortRef.current = null;
      }
    },
    [finishStream, isStreaming, readStream, sessionId],
  );

  const loadSession = useCallback(async (id: string) => {
    abortRef.current?.abort();
    setError(null);
    setStreamingContent("");
    setStreamingSources([]);
    setIsStreaming(false);

    const response = await fetch(`/api/chat/sessions/${encodeURIComponent(id)}`);
    if (!response.ok) {
      setError("Could not load that conversation.");
      return;
    }
    const data = (await response.json()) as ChatSessionDetail;
    setSessionId(data.id);
    setMessages(
      data.messages.map((message) => ({
        id: message.id,
        role: message.role,
        content: message.content,
        sources: [],
        attachments: message.attachments ?? [],
        branchCount: message.branch_count,
        branchIndex: message.branch_index,
      })),
    );
  }, []);

  const stop = useCallback(() => {
    abortRef.current?.abort();
  }, []);

  const reset = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
    setIsStreaming(false);
    setMessages([]);
    setStreamingContent("");
    setStreamingSources([]);
    setSessionId(null);
    setError(null);
  }, []);

  return {
    messages,
    streamingContent,
    streamingSources,
    isStreaming,
    sessionId,
    error,
    send,
    regenerate,
    editMessage,
    stop,
    reset,
    loadSession,
  };
}
