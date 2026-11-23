"use client";

import { useQueryClient } from "@tanstack/react-query";
import {
  type FormEvent,
  type KeyboardEvent,
  useDeferredValue,
  useEffect,
  useRef,
  useState,
} from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import { McpChatPanel } from "@/components/mcp-chat-panel";
import { Button, Modal, Select } from "@/components/ui";
import { useChatStream } from "@/lib/hooks/use-chat-stream";
import {
  chatSessionKeys,
  useChatModels,
  useChatSessions,
  useDeleteChatSession,
  useRenameChatSession,
  useUploadChatAttachment,
} from "@/lib/queries/chat-sessions";
import { useMcpStatus } from "@/lib/queries/mcp";
import { useWorkspaces } from "@/lib/queries/workspaces";
import { useWorkspaceStore } from "@/lib/stores/workspace";
import type { ChatAttachment, ChatSessionSummary, McpStatusServer, Source } from "@/lib/types";

import styles from "./page.module.css";

const SLASH_COMMANDS = [
  { name: "mcp", description: "Inspect MCP servers and tools" },
  { name: "info", description: "Show chat, workspace, and MCP context" },
  { name: "help", description: "List available slash commands" },
  { name: "clear", description: "Clear this conversation" },
  { name: "new", description: "Start a new conversation" },
] as const;

type SlashCommandName = (typeof SLASH_COMMANDS)[number]["name"];

const SUGGESTIONS = [
  "Summarize the documents in this workspace",
  "Find the most relevant information about...",
  "Draft a short plan for...",
  "What MCP tools are available?",
];

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
  const queryClient = useQueryClient();
  const { data: workspaces = [] } = useWorkspaces();
  const [sessionSearch, setSessionSearch] = useState("");
  const deferredSearch = useDeferredValue(sessionSearch);
  const { data: sessions = [] } = useChatSessions(workspaceId, deferredSearch);
  const deleteSession = useDeleteChatSession(workspaceId);
  const renameSession = useRenameChatSession(workspaceId);
  const uploadAttachment = useUploadChatAttachment();
  const { data: modelData } = useChatModels();
  const {
    messages,
    streamingContent,
    streamingSources,
    isStreaming,
    sessionId,
    error,
    send,
    regenerate,
    editMessage,
    reset,
    stop,
    loadSession,
  } = useChatStream();

  const [input, setInput] = useState("");
  const [mcpOpen, setMcpOpen] = useState(false);
  const [infoOpen, setInfoOpen] = useState(false);
  const [helpOpen, setHelpOpen] = useState(false);
  const [historyOpen, setHistoryOpen] = useState(false);
  const [disabledMcpTools, setDisabledMcpTools] = useState<string[]>([]);
  const [slashIndex, setSlashIndex] = useState(0);
  const [slashError, setSlashError] = useState<string | null>(null);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [editingMessageId, setEditingMessageId] = useState<string | null>(null);
  const [renamingSession, setRenamingSession] = useState<ChatSessionSummary | null>(null);
  const [renameValue, setRenameValue] = useState("");
  const [pendingDeleteSession, setPendingDeleteSession] = useState<ChatSessionSummary | null>(null);
  const [sessionActionError, setSessionActionError] = useState<string | null>(null);
  const [model, setModel] = useState("");
  const [attachments, setAttachments] = useState<ChatAttachment[]>([]);
  const [attachmentError, setAttachmentError] = useState<string | null>(null);
  const messageContainer = useRef<HTMLDivElement>(null);
  const composerRef = useRef<HTMLTextAreaElement>(null);
  const attachmentInput = useRef<HTMLInputElement>(null);

  const { data: mcpStatus } = useMcpStatus(infoOpen);

  const slashQuery =
    !editingMessageId && input.startsWith("/") && !input.includes(" ")
      ? input.slice(1).toLowerCase()
      : null;
  const filteredCommands =
    slashQuery === null
      ? []
      : SLASH_COMMANDS.filter((command) => command.name.startsWith(slashQuery));
  const slashOpen = slashQuery !== null && filteredCommands.length > 0 && !isStreaming;
  const currentWorkspace = workspaces.find((workspace) => workspace.id === workspaceId);
  const currentSession = sessions.find((session) => session.id === sessionId);
  const availableModels = modelData?.models ?? [];
  const defaultModel = modelData?.default ?? availableModels[0] ?? "";

  useEffect(() => {
    if (!model && defaultModel) {
      setModel(defaultModel);
    }
  }, [defaultModel, model]);

  useEffect(() => {
    if (currentSession?.model) {
      setModel(currentSession.model);
    }
  }, [currentSession?.model]);

  // biome-ignore lint/correctness/useExhaustiveDependencies: scroll on new content.
  useEffect(() => {
    const container = messageContainer.current;
    if (container) {
      container.scrollTop = container.scrollHeight;
    }
  }, [messages, streamingContent]);

  // biome-ignore lint/correctness/useExhaustiveDependencies: resize with input.
  useEffect(() => {
    const textarea = composerRef.current;
    if (!textarea) {
      return;
    }
    textarea.style.height = "auto";
    textarea.style.height = `${Math.min(textarea.scrollHeight, 180)}px`;
  }, [input]);

  function handleNewChat() {
    reset();
    setDisabledMcpTools([]);
    setMcpOpen(false);
    setInfoOpen(false);
    setHelpOpen(false);
    setSlashError(null);
    setHistoryOpen(false);
    setInput("");
    setSessionSearch("");
    setEditingMessageId(null);
    setModel(defaultModel);
    setAttachments([]);
    setAttachmentError(null);
  }

  async function openSession(id: string) {
    setHistoryOpen(false);
    setDisabledMcpTools([]);
    setEditingMessageId(null);
    setInput("");
    setAttachments([]);
    setAttachmentError(null);
    await loadSession(id);
  }

  function openRenameSession(session: ChatSessionSummary) {
    setRenamingSession(session);
    setRenameValue(session.title);
    setSessionActionError(null);
  }

  async function handleRenameSession() {
    if (!renamingSession) {
      return;
    }
    const title = renameValue.trim();
    if (!title) {
      setSessionActionError("Title is required.");
      return;
    }
    try {
      await renameSession.mutateAsync({
        sessionId: renamingSession.id,
        title,
      });
      setRenamingSession(null);
      setSessionActionError(null);
    } catch {
      setSessionActionError("Could not rename the conversation.");
    }
  }

  function openDeleteSession(session: ChatSessionSummary) {
    setPendingDeleteSession(session);
    setSessionActionError(null);
  }

  async function confirmDeleteSession() {
    if (!pendingDeleteSession) {
      return;
    }
    try {
      await deleteSession.mutateAsync(pendingDeleteSession.id);
      if (sessionId === pendingDeleteSession.id) {
        handleNewChat();
      }
      setPendingDeleteSession(null);
      setSessionActionError(null);
    } catch {
      setSessionActionError("Could not delete the conversation.");
    }
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

  function handleComposerKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (slashOpen) {
      if (event.key === "ArrowDown" || event.key === "ArrowUp") {
        event.preventDefault();
        const delta = event.key === "ArrowDown" ? 1 : -1;
        setSlashIndex(
          (index) => (index + delta + filteredCommands.length) % filteredCommands.length,
        );
        return;
      }
      if (event.key === "Enter" || event.key === "Tab") {
        event.preventDefault();
        runCommand(filteredCommands[slashIndex].name);
        return;
      }
      if (event.key === "Escape") {
        event.preventDefault();
        setInput("");
        return;
      }
    }

    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      void submitMessage();
    }
  }

  async function attachFile(file: File) {
    if (attachments.length >= 5) {
      setAttachmentError("You can attach up to 5 files.");
      return;
    }
    setAttachmentError(null);
    try {
      const uploaded = await uploadAttachment.mutateAsync(file);
      setAttachments((current) => [...current, uploaded]);
    } catch (caught) {
      setAttachmentError(
        caught instanceof Error ? caught.message : "Could not upload the attachment.",
      );
    }
  }

  function removeAttachment(id: string) {
    setAttachments((current) => current.filter((attachment) => attachment.id !== id));
  }

  async function submitMessage() {
    const content = input.trim();
    if (!content || isStreaming) {
      return;
    }

    if (editingMessageId) {
      setInput("");
      setSlashError(null);
      await editMessage(editingMessageId, content, disabledMcpTools);
      setEditingMessageId(null);
      if (sessionId) {
        await loadSession(sessionId);
      }
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
    await send(
      content,
      workspaceId,
      disabledMcpTools,
      model || null,
      attachments.map((attachment) => attachment.id),
      attachments,
    );
    setAttachments([]);
    setAttachmentError(null);
    if (workspaceId) {
      await queryClient.invalidateQueries({
        queryKey: chatSessionKeys.byWorkspace(workspaceId),
      });
    }
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void submitMessage();
  }

  function handleModelChange(next: string) {
    setModel(next);
    if (sessionId) {
      void renameSession.mutate({ sessionId, model: next });
    }
  }

  function startEditing(id: string, content: string) {
    setEditingMessageId(id);
    setInput(content);
    setSlashError(null);
    composerRef.current?.focus();
  }

  function cancelEditing() {
    setEditingMessageId(null);
    setInput("");
  }

  async function regenerateLast() {
    await regenerate(disabledMcpTools);
    if (sessionId) {
      await loadSession(sessionId);
    }
  }

  async function chooseBranch(messageId: string, index: number) {
    const response = await fetch(`/api/chat/messages/${encodeURIComponent(messageId)}/branch`, {
      method: "PATCH",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ index }),
    });
    if (response.ok && sessionId) {
      await loadSession(sessionId);
    }
  }

  async function copyMessage(id: string, content: string) {
    try {
      await navigator.clipboard.writeText(content);
      setCopiedId(id);
      window.setTimeout(() => setCopiedId(null), 1500);
    } catch {
      setCopiedId(null);
    }
  }

  function applySuggestion(text: string) {
    setInput(text);
    composerRef.current?.focus();
  }

  return (
    <div className={styles.page}>
      <aside className={`${styles.history} ${historyOpen ? styles.historyOpen : ""}`}>
        <div className={styles.historyHeader}>
          <span>Chats</span>
          <button
            type="button"
            className={styles.iconButton}
            aria-label="Close chat history"
            onClick={() => setHistoryOpen(false)}
          >
            <svg
              width="18"
              height="18"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              aria-hidden="true"
            >
              <path d="M18 6 6 18M6 6l12 12" />
            </svg>
          </button>
        </div>

        <Button className={styles.newChat} onClick={handleNewChat}>
          New chat
        </Button>

        <input
          className={styles.searchInput}
          type="search"
          value={sessionSearch}
          onChange={(event) => setSessionSearch(event.target.value)}
          placeholder="Search chats..."
          aria-label="Search chats"
        />

        <nav className={styles.sessionList} aria-label="Chat history">
          {sessions.length === 0 ? (
            <p className={styles.sessionEmpty}>
              {sessionSearch.trim() ? "No matching conversations." : "No conversations yet."}
            </p>
          ) : (
            sessions.map((session) => (
              <div
                key={session.id}
                className={`${styles.sessionRow} ${
                  session.id === sessionId ? styles.sessionActive : ""
                }`}
              >
                <button
                  type="button"
                  className={styles.sessionSelect}
                  onClick={() => void openSession(session.id)}
                >
                  <span className={styles.sessionTitle}>{session.title}</span>
                  <span className={styles.sessionMeta}>{session.message_count} messages</span>
                </button>
                <span className={styles.sessionActions}>
                  <button
                    type="button"
                    className={styles.sessionAction}
                    aria-label={`Rename ${session.title}`}
                    onClick={() => openRenameSession(session)}
                  >
                    <svg
                      width="15"
                      height="15"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="2"
                      aria-hidden="true"
                    >
                      <path d="M12 20h9" />
                      <path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L8 18l-4 1 1-4Z" />
                    </svg>
                  </button>
                  <button
                    type="button"
                    className={styles.sessionAction}
                    aria-label={`Delete ${session.title}`}
                    onClick={() => openDeleteSession(session)}
                  >
                    <svg
                      width="15"
                      height="15"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="2"
                      aria-hidden="true"
                    >
                      <path d="M3 6h18M8 6V4h8v2m-9 0 1 14h8l1-14" />
                    </svg>
                  </button>
                </span>
              </div>
            ))
          )}
        </nav>

        <div className={styles.historyFooter}>
          <span>{currentWorkspace?.name ?? "No workspace"}</span>
          <button type="button" className={styles.footerCommand} onClick={() => setMcpOpen(true)}>
            /mcp tools
          </button>
        </div>
      </aside>

      {historyOpen ? (
        <button
          type="button"
          className={styles.historyOverlay}
          aria-label="Close chat history"
          onClick={() => setHistoryOpen(false)}
        />
      ) : null}

      <section className={styles.thread}>
        <header className={styles.threadHeader}>
          <button
            type="button"
            className={styles.iconButton}
            aria-label="Open chat history"
            onClick={() => setHistoryOpen(true)}
          >
            <svg
              width="20"
              height="20"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              aria-hidden="true"
            >
              <line x1="3" y1="6" x2="21" y2="6" />
              <line x1="3" y1="12" x2="21" y2="12" />
              <line x1="3" y1="18" x2="21" y2="18" />
            </svg>
          </button>

          <div className={styles.threadTitle}>
            <strong>{currentSession?.title ?? "New chat"}</strong>
            <span>{currentWorkspace?.name ?? "No workspace selected"}</span>
          </div>

          {availableModels.length > 0 ? (
            <div className={styles.modelPicker}>
              <Select
                label="Chat model"
                value={model || defaultModel}
                onChange={handleModelChange}
                options={availableModels.map((name) => ({ value: name, label: name }))}
              />
            </div>
          ) : null}

          <Button size="sm" variant="ghost" onClick={() => setMcpOpen(true)}>
            MCP
          </Button>
        </header>

        <div ref={messageContainer} className={styles.messages}>
          {messages.length === 0 && !isStreaming ? (
            <div className={styles.empty}>
              <div className={styles.emptyMark} aria-hidden="true">
                AI
              </div>
              <h1 className={styles.emptyTitle}>How can I help you today?</h1>
              <p className={styles.emptySubtitle}>
                Ask about your workspace documents, run tools, or type <code>/</code> for commands.
              </p>
              <div className={styles.suggestions}>
                {SUGGESTIONS.map((suggestion) => (
                  <button
                    key={suggestion}
                    type="button"
                    className={styles.suggestion}
                    onClick={() => applySuggestion(suggestion)}
                  >
                    {suggestion}
                  </button>
                ))}
              </div>
            </div>
          ) : null}

          <div className={styles.messageList}>
            {messages.map((message, index) => (
              <div
                key={message.id}
                className={`${styles.messageRow} ${message.role === "user" ? styles.userRow : ""}`}
              >
                {message.role === "assistant" ? (
                  <div className={styles.avatar} aria-hidden="true">
                    AI
                  </div>
                ) : null}
                <div
                  className={`${styles.messageBody} ${
                    message.role === "user" ? styles.userBody : ""
                  }`}
                >
                  <div className={styles.messageMeta}>
                    {message.role === "user" ? "You" : "AI Workspace"}
                  </div>
                  {message.role === "assistant" ? (
                    <div className={styles.markdown}>
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown>
                    </div>
                  ) : (
                    <>
                      {message.attachments?.some((attachment) => attachment.is_image) ? (
                        <div className={styles.messageImages}>
                          {message.attachments
                            .filter((attachment) => attachment.is_image)
                            .map((attachment) => (
                              /* biome-ignore lint/performance/noImgElement: dynamic user-uploaded image served by the API */
                              <img
                                key={attachment.id}
                                className={styles.messageImage}
                                src={`/api/chat/attachments/${encodeURIComponent(attachment.id)}/file`}
                                alt={attachment.filename}
                                loading="lazy"
                              />
                            ))}
                        </div>
                      ) : null}
                      <div className={styles.userText}>{message.content}</div>
                    </>
                  )}
                  {message.role === "assistant" ? <SourceList sources={message.sources} /> : null}
                  <div className={styles.messageActions}>
                    {message.role === "assistant" ? (
                      <button
                        type="button"
                        className={styles.copyButton}
                        onClick={() => void copyMessage(message.id, message.content)}
                      >
                        {copiedId === message.id ? "Copied" : "Copy"}
                      </button>
                    ) : null}
                    {message.role === "assistant" &&
                    sessionId &&
                    index === messages.length - 1 &&
                    !isStreaming ? (
                      <button
                        type="button"
                        className={styles.copyButton}
                        onClick={() => void regenerateLast()}
                      >
                        Regenerate
                      </button>
                    ) : null}
                    {message.role === "user" && !isStreaming ? (
                      <button
                        type="button"
                        className={`${styles.copyButton} ${styles.userAction}`}
                        onClick={() => startEditing(message.id, message.content)}
                      >
                        Edit
                      </button>
                    ) : null}
                    {(message.branchCount ?? 1) > 1 ? (
                      <span className={styles.branchControls}>
                        <button
                          type="button"
                          className={styles.branchButton}
                          aria-label="Previous branch"
                          disabled={(message.branchIndex ?? 0) === 0}
                          onClick={() =>
                            void chooseBranch(message.id, (message.branchIndex ?? 0) - 1)
                          }
                        >
                          &lt;
                        </button>
                        <span>
                          {(message.branchIndex ?? 0) + 1}/{message.branchCount}
                        </span>
                        <button
                          type="button"
                          className={styles.branchButton}
                          aria-label="Next branch"
                          disabled={(message.branchIndex ?? 0) + 1 >= (message.branchCount ?? 1)}
                          onClick={() =>
                            void chooseBranch(message.id, (message.branchIndex ?? 0) + 1)
                          }
                        >
                          &gt;
                        </button>
                      </span>
                    ) : null}
                  </div>
                </div>
              </div>
            ))}

            {isStreaming ? (
              <div className={`${styles.messageRow} ${styles.assistantRow}`}>
                <div className={styles.avatar} aria-hidden="true">
                  AI
                </div>
                <div className={styles.messageBody}>
                  <div className={styles.messageMeta}>AI Workspace</div>
                  <div className={styles.markdown}>
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>{streamingContent}</ReactMarkdown>
                    <span className={styles.cursor} aria-hidden="true">
                      |
                    </span>
                  </div>
                  <SourceList sources={streamingSources} />
                </div>
              </div>
            ) : null}
          </div>

          {error ? <div className={styles.error}>{error}</div> : null}
        </div>

        <div className={styles.composerArea}>
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

            {editingMessageId ? (
              <div className={styles.editingBanner}>
                <span>Editing message</span>
                <button type="button" onClick={cancelEditing}>
                  Cancel
                </button>
              </div>
            ) : null}

            {attachments.length > 0 ? (
              <div className={styles.attachmentBar}>
                {attachments.map((attachment) => (
                  <span key={attachment.id} className={styles.attachmentChip}>
                    {attachment.is_image ? (
                      /* biome-ignore lint/performance/noImgElement: dynamic user-uploaded image served by the API */
                      <img
                        className={styles.attachmentThumb}
                        src={`/api/chat/attachments/${encodeURIComponent(attachment.id)}/file`}
                        alt=""
                        loading="lazy"
                      />
                    ) : null}
                    <span className={styles.attachmentName}>{attachment.filename}</span>
                    <button
                      type="button"
                      aria-label={`Remove ${attachment.filename}`}
                      onClick={() => removeAttachment(attachment.id)}
                    >
                      x
                    </button>
                  </span>
                ))}
              </div>
            ) : null}
            {attachmentError ? <p className={styles.slashError}>{attachmentError}</p> : null}

            <form className={styles.composer} onSubmit={handleSubmit}>
              <input
                ref={attachmentInput}
                type="file"
                className={styles.hiddenFile}
                multiple
                accept=".pdf,.md,.markdown,.csv,.txt,.json,.yaml,.yml,.py,.js,.jsx,.ts,.tsx,.rs,.go,.java,.png,.jpg,.jpeg,.webp,.gif"
                aria-label="Attach files"
                onChange={(event) => {
                  const files = Array.from(event.target.files ?? []);
                  for (const file of files.slice(0, 5 - attachments.length)) {
                    void attachFile(file);
                  }
                  event.target.value = "";
                }}
              />
              <button
                type="button"
                className={styles.attachButton}
                aria-label="Attach files"
                onClick={() => attachmentInput.current?.click()}
                disabled={
                  isStreaming ||
                  Boolean(editingMessageId) ||
                  attachments.length >= 5 ||
                  uploadAttachment.isPending
                }
              >
                <svg
                  width="18"
                  height="18"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  aria-hidden="true"
                >
                  <path d="m21.4 11.6-8.5 8.5a6 6 0 0 1-8.5-8.5l9.2-9.2a4 4 0 0 1 5.7 5.7l-9.2 9.2a2 2 0 0 1-2.8-2.8l8.5-8.5" />
                </svg>
              </button>
              <textarea
                ref={composerRef}
                className={styles.composerInput}
                value={input}
                onChange={(event) => {
                  setInput(event.target.value);
                  setSlashError(null);
                  setSlashIndex(0);
                }}
                onKeyDown={handleComposerKeyDown}
                placeholder={
                  editingMessageId ? "Update your message..." : "Message AI Workspace..."
                }
                aria-label="Chat message"
                role="combobox"
                aria-autocomplete="list"
                aria-expanded={slashOpen}
                aria-controls={slashOpen ? "slash-menu" : undefined}
                aria-activedescendant={
                  slashOpen ? `slash-command-${filteredCommands[slashIndex]?.name}` : undefined
                }
                rows={1}
                disabled={isStreaming}
              />
              {isStreaming ? (
                <Button type="button" variant="secondary" onClick={stop}>
                  Stop
                </Button>
              ) : (
                <Button type="submit" disabled={!input.trim()}>
                  {editingMessageId ? "Update" : "Send"}
                </Button>
              )}
            </form>
          </div>
          <p className={styles.composerHint}>
            Enter to send, Shift+Enter for a new line. Type <code>/</code> for commands.
          </p>
        </div>
      </section>

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

      <Modal
        open={Boolean(renamingSession)}
        onClose={() => setRenamingSession(null)}
        title="Rename conversation"
        footer={
          <>
            <Button variant="ghost" onClick={() => setRenamingSession(null)}>
              Cancel
            </Button>
            <Button loading={renameSession.isPending} onClick={() => void handleRenameSession()}>
              Save
            </Button>
          </>
        }
      >
        <label className={styles.renameField}>
          <span>Title</span>
          <input
            className={styles.renameInput}
            value={renameValue}
            onChange={(event) => setRenameValue(event.target.value)}
            maxLength={255}
            aria-label="Conversation title"
          />
        </label>
        {sessionActionError ? <p className={styles.error}>{sessionActionError}</p> : null}
      </Modal>

      <Modal
        open={Boolean(pendingDeleteSession)}
        onClose={() => setPendingDeleteSession(null)}
        title="Delete conversation"
        footer={
          <>
            <Button variant="ghost" onClick={() => setPendingDeleteSession(null)}>
              Cancel
            </Button>
            <Button
              variant="danger"
              loading={deleteSession.isPending}
              onClick={() => void confirmDeleteSession()}
            >
              Delete
            </Button>
          </>
        }
      >
        <p>
          Delete <strong>{pendingDeleteSession?.title}</strong>? This removes the conversation and
          all of its messages.
        </p>
        {sessionActionError ? <p className={styles.error}>{sessionActionError}</p> : null}
      </Modal>
    </div>
  );
}
