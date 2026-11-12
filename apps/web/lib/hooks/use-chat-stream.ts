"use client";

import { useCallback, useRef, useState } from "react";

import type { ChatMessage, ChatRole, Source } from "@/lib/types";

interface StreamPayload {
  token?: string;
  session_id?: string;
  event?: string;
  sources?: Source[];
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

  const send = useCallback(
    async (content: string, workspaceId: string | null) => {
      if (!content.trim() || isStreaming) {
        return;
      }

      setError(null);
      setMessages((previous) => [...previous, createMessage("user", content)]);
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
          }),
          signal: controller.signal,
        });

        if (!response.ok || !response.body) {
          throw new Error("Chat request failed");
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";
        let accumulated = "";
        let accumulatedSources: Source[] = [];

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
            }
          }
        }

        if (accumulated) {
          setMessages((previous) => [
            ...previous,
            createMessage("assistant", accumulated, accumulatedSources),
          ]);
        }
        setStreamingContent("");
        setStreamingSources([]);
      } catch (caught) {
        if (caught instanceof DOMException && caught.name === "AbortError") {
          return;
        }
        setError("Sorry, I encountered an error. Please try again.");
      } finally {
        setIsStreaming(false);
        abortRef.current = null;
      }
    },
    [isStreaming, sessionId],
  );

  const stop = useCallback(() => {
    abortRef.current?.abort();
  }, []);

  const reset = useCallback(() => {
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
    stop,
    reset,
  };
}
