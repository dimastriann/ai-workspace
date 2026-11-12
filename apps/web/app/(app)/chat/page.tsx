"use client";

import { type FormEvent, useEffect, useRef, useState } from "react";

import { Button, Card } from "@/components/ui";
import { useChatStream } from "@/lib/hooks/use-chat-stream";
import { useWorkspaceStore } from "@/lib/stores/workspace";
import type { Source } from "@/lib/types";

import styles from "./page.module.css";

function SourceList({ sources }: { sources?: Source[] }) {
  if (!sources?.length) {
    return null;
  }

  return (
    <div className={styles.sources}>
      {sources.map((source) => (
        <span
          key={`${source.document_id}-${source.ordinal}`}
          className={styles.source}
          title={source.snippet}
        >
          {source.filename} · chunk {source.ordinal + 1}
        </span>
      ))}
    </div>
  );
}

export default function ChatPage() {
  const workspaceId = useWorkspaceStore((state) => state.currentWorkspaceId);
  const { messages, streamingContent, streamingSources, isStreaming, error, send, reset } =
    useChatStream();
  const [input, setInput] = useState("");
  const messageContainer = useRef<HTMLDivElement>(null);

  // biome-ignore lint/correctness/useExhaustiveDependencies: scroll on new content.
  useEffect(() => {
    const container = messageContainer.current;
    if (container) {
      container.scrollTop = container.scrollHeight;
    }
  }, [messages, streamingContent]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const content = input;
    setInput("");
    await send(content, workspaceId);
  }

  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <h1 className={styles.title}>AI Chat</h1>
        <p className={styles.secondary}>Interactive conversational AI with context awareness.</p>
      </header>

      <div className={styles.chatLayout}>
        <aside className={`${styles.sessions} glass`}>
          <Button variant="primary" className={styles.newChat} onClick={reset}>
            + New Chat
          </Button>
          <div className={styles.sessionList} />
        </aside>

        <Card className={`${styles.chatWrapper} glass`}>
          <div ref={messageContainer} className={styles.messages}>
            {messages.length === 0 && !isStreaming ? (
              <div className={styles.empty}>
                <span className={styles.emptyIcon} aria-hidden="true">
                  ✨
                </span>
                <p>How can I help you today?</p>
              </div>
            ) : null}

            {messages.map((message) => (
              <div key={message.id} className={`${styles.message} ${styles[message.role]}`}>
                <div className={styles.messageContent}>
                  <div className={styles.roleBadge}>{message.role === "user" ? "You" : "AI"}</div>
                  <div className={styles.text}>{message.content}</div>
                </div>
                {message.role === "assistant" ? <SourceList sources={message.sources} /> : null}
              </div>
            ))}

            {isStreaming ? (
              <div className={`${styles.message} ${styles.assistant}`}>
                <div className={styles.messageContent}>
                  <div className={styles.roleBadge}>AI</div>
                  <div className={styles.text}>
                    {streamingContent}
                    <span className={styles.cursor} aria-hidden="true">
                      |
                    </span>
                  </div>
                </div>
                <SourceList sources={streamingSources} />
              </div>
            ) : null}

            {error ? <div className={styles.error}>{error}</div> : null}
          </div>

          <form className={styles.inputArea} onSubmit={handleSubmit}>
            <input
              className={styles.input}
              value={input}
              onChange={(event) => setInput(event.target.value)}
              placeholder="Type your message..."
              disabled={isStreaming}
            />
            <Button type="submit" loading={isStreaming} disabled={!input.trim()}>
              Send
            </Button>
          </form>
        </Card>
      </div>
    </div>
  );
}
