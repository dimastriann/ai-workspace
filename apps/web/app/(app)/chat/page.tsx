"use client";

import { type FormEvent, type KeyboardEvent, useEffect, useRef, useState } from "react";

import { McpChatPanel } from "@/components/mcp-chat-panel";
import { Button, Card, Modal } from "@/components/ui";
import { useChatStream } from "@/lib/hooks/use-chat-stream";
import { useMcpStatus } from "@/lib/queries/mcp";
import { useWorkspaces } from "@/lib/queries/workspaces";
import { useWorkspaceStore } from "@/lib/stores/workspace";
import type { McpStatusServer, Source } from "@/lib/types";

import styles from "./page.module.css";

const SLASH_COMMANDS = [
  { name: "mcp", description: "Inspect MCP servers and tools" },
  { name: "info", description: "Show chat, workspace, and MCP context" },
  { name: "help", description: "List available slash commands" },
  { name: "clear", description: "Clear this conversation" },
  { name: "new", description: "Start a new conversation" },
] as const;

type SlashCommandName = (typeof SLASH_COMMANDS)[number]["name"];

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
          {source.filename} - chunk {source.ordinal + 1}
        </span>
      ))}
    </div>
  );
}

export default function ChatPage() {
  const workspaceId = useWorkspaceStore((state) => state.currentWorkspaceId);
  const {
    messages,
    streamingContent,
    streamingSources,
    isStreaming,
    sessionId,
    error,
    send,
    reset,
  } = useChatStream();
  const [input, setInput] = useState("");
  const [mcpOpen, setMcpOpen] = useState(false);
  const [infoOpen, setInfoOpen] = useState(false);
  const [helpOpen, setHelpOpen] = useState(false);
  const [disabledMcpTools, setDisabledMcpTools] = useState<string[]>([]);
  const [slashIndex, setSlashIndex] = useState(0);
  const [slashError, setSlashError] = useState<string | null>(null);
  const messageContainer = useRef<HTMLDivElement>(null);
  const { data: workspaces = [] } = useWorkspaces();
  const { data: mcpStatus } = useMcpStatus(infoOpen);

  const slashQuery =
    input.startsWith("/") && !input.includes(" ") ? input.slice(1).toLowerCase() : null;
  const filteredCommands =
    slashQuery === null
      ? []
      : SLASH_COMMANDS.filter((command) => command.name.startsWith(slashQuery));
  const slashOpen = slashQuery !== null && filteredCommands.length > 0 && !isStreaming;
  const currentWorkspace = workspaces.find((workspace) => workspace.id === workspaceId);

  // biome-ignore lint/correctness/useExhaustiveDependencies: scroll on new content.
  useEffect(() => {
    const container = messageContainer.current;
    if (container) {
      container.scrollTop = container.scrollHeight;
    }
  }, [messages, streamingContent]);

  function handleNewChat() {
    reset();
    setDisabledMcpTools([]);
    setMcpOpen(false);
    setInfoOpen(false);
    setHelpOpen(false);
  }

  function runCommand(command: SlashCommandName) {
    setInput("");
    setSlashIndex(0);
    setSlashError(null);

    switch (command) {
      case "mcp":
        setMcpOpen(true);
        break;
      case "info":
        setInfoOpen(true);
        break;
      case "help":
        setHelpOpen(true);
        break;
      case "clear":
      case "new":
        handleNewChat();
        break;
    }
  }

  function handleComposerKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (!slashOpen) {
      return;
    }

    if (event.key === "ArrowDown" || event.key === "ArrowUp") {
      event.preventDefault();
      const delta = event.key === "ArrowDown" ? 1 : -1;
      setSlashIndex((index) => (index + delta + filteredCommands.length) % filteredCommands.length);
    } else if (event.key === "Enter" || event.key === "Tab") {
      event.preventDefault();
      runCommand(filteredCommands[slashIndex].name);
    } else if (event.key === "Escape") {
      event.preventDefault();
      setInput("");
    }
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const content = input.trim();
    if (!content) {
      return;
    }

    if (content.startsWith("/") && !content.includes(" ")) {
      const command = SLASH_COMMANDS.find((item) => item.name === content.slice(1).toLowerCase());
      if (command) {
        runCommand(command.name);
      } else {
        setInput("");
        setSlashError(`Unknown command: ${content}`);
      }
      return;
    }

    setInput("");
    setSlashError(null);
    await send(content, workspaceId, disabledMcpTools);
  }

  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <h1 className={styles.title}>AI Chat</h1>
        <p className={styles.secondary}>Interactive conversational AI with context awareness.</p>
      </header>

      <Button variant="primary" className={styles.mobileNewChat} onClick={handleNewChat}>
        + New Chat
      </Button>

      <div className={styles.chatLayout}>
        <aside className={`${styles.sessions} glass`}>
          <Button variant="primary" className={styles.newChat} onClick={handleNewChat}>
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
                <p className={styles.commandHint}>
                  Type <code>/mcp</code> to inspect MCP tools.
                </p>
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

          <div className={styles.composerWrap}>
            {slashOpen ? (
              <div
                id="slash-menu"
                className={styles.slashMenu}
                role="listbox"
                aria-label="Slash commands"
              >
                {filteredCommands.map((command, index) => (
                  <button
                    key={command.name}
                    id={`slash-command-${command.name}`}
                    type="button"
                    role="option"
                    aria-selected={index === slashIndex}
                    className={`${styles.slashOption} ${
                      index === slashIndex ? styles.slashActive : ""
                    }`}
                    onMouseDown={(event) => event.preventDefault()}
                    onMouseEnter={() => setSlashIndex(index)}
                    onClick={() => runCommand(command.name)}
                  >
                    <span className={styles.slashName}>/{command.name}</span>
                    <span className={styles.slashDesc}>{command.description}</span>
                  </button>
                ))}
              </div>
            ) : null}

            {slashError ? <p className={styles.slashError}>{slashError}</p> : null}

            <form className={styles.inputArea} onSubmit={handleSubmit}>
              <input
                className={styles.input}
                value={input}
                onChange={(event) => {
                  setInput(event.target.value);
                  setSlashError(null);
                  setSlashIndex(0);
                }}
                onKeyDown={handleComposerKeyDown}
                placeholder="Message... or type /"
                aria-label="Chat message"
                role="combobox"
                aria-autocomplete="list"
                aria-expanded={slashOpen}
                aria-controls={slashOpen ? "slash-menu" : undefined}
                aria-activedescendant={
                  slashOpen ? `slash-command-${filteredCommands[slashIndex]?.name}` : undefined
                }
                disabled={isStreaming}
              />
              <Button type="submit" loading={isStreaming} disabled={!input.trim()}>
                Send
              </Button>
            </form>
          </div>
        </Card>
      </div>

      <McpChatPanel
        open={mcpOpen}
        onClose={() => setMcpOpen(false)}
        disabledTools={disabledMcpTools}
        onToggleTool={(toolName, enabled) =>
          setDisabledMcpTools((current) =>
            enabled ? current.filter((name) => name !== toolName) : [...current, toolName],
          )
        }
        onToggleServer={(server: McpStatusServer, enabled) => {
          const names = server.tools.map((tool) => tool.name);
          setDisabledMcpTools((current) =>
            enabled
              ? current.filter((name) => !names.includes(name))
              : Array.from(new Set([...current, ...names])),
          );
        }}
      />

      <Modal
        open={infoOpen}
        onClose={() => setInfoOpen(false)}
        title="Chat info"
        footer={
          <Button variant="secondary" onClick={() => setInfoOpen(false)}>
            Close
          </Button>
        }
      >
        <dl className={styles.infoGrid}>
          <div>
            <dt>Workspace</dt>
            <dd>{currentWorkspace?.name ?? "Not selected"}</dd>
          </div>
          <div>
            <dt>Session</dt>
            <dd>{sessionId ?? "New conversation"}</dd>
          </div>
          <div>
            <dt>Messages</dt>
            <dd>{messages.length}</dd>
          </div>
          <div>
            <dt>MCP</dt>
            <dd>
              {mcpStatus
                ? mcpStatus.feature_enabled
                  ? `${mcpStatus.servers.length} servers - ${mcpStatus.servers.reduce(
                      (total, server) => total + server.tools.length,
                      0,
                    )} tools`
                  : "Disabled globally"
                : "Loading..."}
            </dd>
          </div>
        </dl>
        <p className={styles.infoHint}>
          Use <code>/mcp</code> to inspect and toggle MCP tools for this chat.
        </p>
      </Modal>

      <Modal
        open={helpOpen}
        onClose={() => setHelpOpen(false)}
        title="Slash commands"
        footer={
          <Button variant="secondary" onClick={() => setHelpOpen(false)}>
            Close
          </Button>
        }
      >
        <ul className={styles.commandList}>
          {SLASH_COMMANDS.map((command) => (
            <li key={command.name}>
              <code>/{command.name}</code>
              <span>{command.description}</span>
            </li>
          ))}
        </ul>
      </Modal>
    </div>
  );
}
