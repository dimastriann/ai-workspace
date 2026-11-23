"use client";

import { useState } from "react";

import { Button, Card, Modal, Select, Switch } from "@/components/ui";
import {
  type McpServerInput,
  useCreateMcpServer,
  useDeleteMcpServer,
  useDisconnectMcpOAuth,
  useMcpServers,
  useStartMcpOAuth,
  useTestMcpServer,
  useUpdateMcpServer,
} from "@/lib/queries/mcp";
import type { McpServer, McpTool } from "@/lib/types";

import styles from "./mcp-servers-panel.module.css";

interface McpServersPanelProps {
  enabled: boolean;
}

export function McpServersPanel({ enabled }: McpServersPanelProps) {
  const { data: servers = [], isLoading } = useMcpServers();
  const createServer = useCreateMcpServer();
  const updateServer = useUpdateMcpServer();
  const deleteServer = useDeleteMcpServer();
  const testServer = useTestMcpServer();
  const startOAuth = useStartMcpOAuth();
  const disconnectOAuth = useDisconnectMcpOAuth();
  const [oauthError, setOauthError] = useState<string | null>(null);

  const [editorOpen, setEditorOpen] = useState(false);
  const [editing, setEditing] = useState<McpServer | null>(null);
  const [name, setName] = useState("");
  const [transport, setTransport] = useState<"http" | "sse" | "stdio">("http");
  const [url, setUrl] = useState("");
  const [commandText, setCommandText] = useState("");
  const [envText, setEnvText] = useState("");
  const [headersText, setHeadersText] = useState("");
  const [timeoutSeconds, setTimeoutSeconds] = useState("10");
  const [serverEnabled, setServerEnabled] = useState(true);
  const [editorError, setEditorError] = useState<string | null>(null);

  const [pendingDelete, setPendingDelete] = useState<McpServer | null>(null);
  const [testingId, setTestingId] = useState<string | null>(null);
  const [toolServer, setToolServer] = useState<McpServer | null>(null);
  const [tools, setTools] = useState<McpTool[]>([]);
  const [disabledTools, setDisabledTools] = useState<string[]>([]);
  const [toolError, setToolError] = useState<string | null>(null);

  function openCreate() {
    setEditing(null);
    setName("");
    setTransport("http");
    setUrl("");
    setCommandText("");
    setEnvText("");
    setHeadersText("");
    setTimeoutSeconds("10");
    setServerEnabled(true);
    setEditorError(null);
    setEditorOpen(true);
  }

  function openEdit(server: McpServer) {
    setEditing(server);
    setName(server.name);
    setTransport(server.transport);
    setUrl(server.url);
    setCommandText("");
    setEnvText("");
    setHeadersText("");
    setTimeoutSeconds(String(server.timeout_seconds));
    setServerEnabled(server.enabled);
    setEditorError(null);
    setEditorOpen(true);
  }

  function closeEditor() {
    setEditorOpen(false);
    setEditing(null);
    setEditorError(null);
  }

  function parseHeaders(): Record<string, string> | null | "keep" | undefined {
    const text = headersText.trim();
    if (!text) {
      return editing ? "keep" : null;
    }
    try {
      const parsed = JSON.parse(text) as unknown;
      if (
        typeof parsed !== "object" ||
        parsed === null ||
        Array.isArray(parsed) ||
        Object.values(parsed).some((value) => typeof value !== "string")
      ) {
        throw new Error("invalid");
      }
      return parsed as Record<string, string>;
    } catch {
      setEditorError('Headers must be a JSON object, e.g. {"Authorization": "Bearer ..."}');
      return undefined;
    }
  }

  function parseCommand(): string[] | null | "keep" | undefined {
    const text = commandText.trim();
    if (!text) {
      return editing ? "keep" : null;
    }
    try {
      const parsed = JSON.parse(text) as unknown;
      if (
        !Array.isArray(parsed) ||
        parsed.some((item) => typeof item !== "string") ||
        parsed.length === 0
      ) {
        throw new Error("invalid");
      }
      return parsed as string[];
    } catch {
      setEditorError('Command must be a JSON array of strings, e.g. ["uvx", "mcp-server-git"]');
      return undefined;
    }
  }

  function parseEnv(): Record<string, string> | null | "keep" | undefined {
    const text = envText.trim();
    if (!text) {
      return editing ? "keep" : null;
    }
    try {
      const parsed = JSON.parse(text) as unknown;
      if (
        typeof parsed !== "object" ||
        parsed === null ||
        Array.isArray(parsed) ||
        Object.values(parsed).some((value) => typeof value !== "string")
      ) {
        throw new Error("invalid");
      }
      return parsed as Record<string, string>;
    } catch {
      setEditorError('Environment must be a JSON object, e.g. {"API_KEY": "..."}');
      return undefined;
    }
  }

  async function saveServer() {
    const trimmedName = name.trim();
    const trimmedUrl = url.trim();
    const timeout = Number.parseInt(timeoutSeconds, 10);
    const isStdio = transport === "stdio";
    if (!trimmedName || (!isStdio && !trimmedUrl)) {
      setEditorError(isStdio ? "Name is required." : "Name and URL are required.");
      return;
    }
    if (!Number.isFinite(timeout) || timeout < 1 || timeout > 60) {
      setEditorError("Timeout must be between 1 and 60 seconds.");
      return;
    }

    const headers = parseHeaders();
    if (headers === undefined) {
      return;
    }
    const command = parseCommand();
    if (command === undefined) {
      return;
    }
    const env = parseEnv();
    if (env === undefined) {
      return;
    }

    const input: McpServerInput = {
      name: trimmedName,
      transport,
      url: isStdio ? "" : trimmedUrl,
      enabled: serverEnabled,
      timeout_seconds: timeout,
      ...(command && command !== "keep" ? { command } : {}),
      ...(env && env !== "keep" ? { env } : {}),
      ...(headers && headers !== "keep" ? { headers } : {}),
    };

    setEditorError(null);
    try {
      if (editing) {
        await updateServer.mutateAsync({ serverId: editing.id, ...input });
      } else {
        await createServer.mutateAsync(input);
      }
      closeEditor();
    } catch {
      setEditorError(
        "Could not save the server. Check the URL/command, name uniqueness, and network reachability.",
      );
    }
  }

  async function testConnection(server: McpServer) {
    setTestingId(server.id);
    setToolError(null);
    try {
      const result = await testServer.mutateAsync(server.id);
      setToolServer(server);
      setTools(result.tools);
      setDisabledTools(server.disabled_tools);
      if (!result.ok) {
        setToolError(result.error ?? "Connection failed.");
      }
    } catch {
      setToolServer(server);
      setTools([]);
      setDisabledTools(server.disabled_tools);
      setToolError("Connection failed.");
    } finally {
      setTestingId(null);
    }
  }

  async function saveTools() {
    if (!toolServer) {
      return;
    }
    try {
      await updateServer.mutateAsync({
        serverId: toolServer.id,
        disabled_tools: disabledTools,
      });
      setToolServer(null);
      setTools([]);
    } catch {
      setToolError("Failed to save tool settings.");
    }
  }

  async function connectOAuth(server: McpServer) {
    setOauthError(null);
    try {
      const result = await startOAuth.mutateAsync(server.id);
      window.open(result.authorize_url, "_blank", "noopener,width=600,height=720");
    } catch {
      setOauthError(`Could not start the OAuth flow for ${server.name}.`);
    }
  }

  async function removeOAuth(server: McpServer) {
    setOauthError(null);
    try {
      await disconnectOAuth.mutateAsync(server.id);
    } catch {
      setOauthError(`Could not disconnect OAuth for ${server.name}.`);
    }
  }

  async function handleDelete() {
    if (!pendingDelete) {
      return;
    }
    try {
      await deleteServer.mutateAsync(pendingDelete.id);
      setPendingDelete(null);
    } catch {
      setPendingDelete(null);
    }
  }

  return (
    <>
      <Card
        header={
          <div className={styles.headerRow}>
            <span>MCP servers</span>
            <Button size="sm" variant="secondary" onClick={openCreate}>
              Add server
            </Button>
          </div>
        }
      >
        {!enabled ? (
          <p className={styles.notice}>
            MCP is disabled. Enable <code>features.mcp</code> above to expose discovered tools to
            agents.
          </p>
        ) : null}

        {oauthError ? <p className={styles.error}>{oauthError}</p> : null}

        {isLoading ? (
          <p className={styles.notice}>Loading MCP servers…</p>
        ) : servers.length === 0 ? (
          <p className={styles.notice}>
            No MCP servers configured. Add a remote MCP endpoint or a local stdio process to give
            agents access to tools such as GitHub, Jira, or Lark.
          </p>
        ) : (
          <div className={styles.list}>
            {servers.map((server) => (
              <div key={server.id} className={styles.server}>
                <div className={styles.serverInfo}>
                  <div className={styles.serverNameRow}>
                    <strong>{server.name}</strong>
                    <span className={styles.transport}>{server.transport}</span>
                    {server.last_status ? (
                      <span
                        className={`${styles.status} ${
                          server.last_status === "ok" ? styles.ok : styles.fail
                        }`}
                      >
                        {server.last_status}
                      </span>
                    ) : null}
                  </div>
                  <span className={styles.url}>
                    {server.transport === "stdio" ? (server.command ?? []).join(" ") : server.url}
                  </span>
                  {server.transport === "stdio" && server.env_names.length > 0 ? (
                    <span className={styles.meta}>Env: {server.env_names.join(", ")} (masked)</span>
                  ) : null}
                  {server.header_names.length > 0 ? (
                    <span className={styles.meta}>
                      Headers: {server.header_names.join(", ")} (masked)
                    </span>
                  ) : null}
                  {server.last_error ? (
                    <span className={styles.error}>{server.last_error}</span>
                  ) : null}
                </div>

                <div className={styles.actions}>
                  <Switch
                    label={`Enable ${server.name}`}
                    checked={server.enabled}
                    onChange={(checked) =>
                      updateServer.mutate({ serverId: server.id, enabled: checked })
                    }
                  />
                  {server.transport !== "stdio" ? (
                    server.oauth_connected ? (
                      <Button
                        size="sm"
                        variant="ghost"
                        loading={disconnectOAuth.isPending}
                        onClick={() => removeOAuth(server)}
                      >
                        Disconnect OAuth
                      </Button>
                    ) : (
                      <Button
                        size="sm"
                        variant="secondary"
                        loading={startOAuth.isPending}
                        onClick={() => connectOAuth(server)}
                      >
                        Connect OAuth
                      </Button>
                    )
                  ) : null}
                  <Button
                    size="sm"
                    variant="secondary"
                    loading={testingId === server.id}
                    onClick={() => testConnection(server)}
                  >
                    Test
                  </Button>
                  <Button size="sm" variant="ghost" onClick={() => openEdit(server)}>
                    Edit
                  </Button>
                  <Button size="sm" variant="danger" onClick={() => setPendingDelete(server)}>
                    Delete
                  </Button>
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>

      <Modal
        open={editorOpen}
        onClose={closeEditor}
        title={editing ? "Edit MCP server" : "Add MCP server"}
        footer={
          <>
            <Button variant="ghost" onClick={closeEditor}>
              Cancel
            </Button>
            <Button loading={createServer.isPending || updateServer.isPending} onClick={saveServer}>
              Save
            </Button>
          </>
        }
      >
        <div className={styles.form}>
          <label className={styles.field}>
            <span>Name</span>
            <input
              className={styles.input}
              value={name}
              onChange={(event) => setName(event.target.value)}
              maxLength={120}
            />
          </label>

          <div className={styles.field}>
            <span>Transport</span>
            <Select
              label="Transport"
              value={transport}
              onChange={(next) => setTransport(next as "http" | "sse" | "stdio")}
              options={[
                { value: "http", label: "Streamable HTTP" },
                { value: "sse", label: "HTTP + SSE (legacy)" },
                { value: "stdio", label: "Local process (stdio)" },
              ]}
            />
          </div>

          {transport === "stdio" ? (
            <>
              <label className={styles.field}>
                <span>
                  Command {editing?.command ? "(leave blank to keep existing)" : "(JSON array)"}
                </span>
                <input
                  className={styles.input}
                  value={commandText}
                  onChange={(event) => setCommandText(event.target.value)}
                  placeholder='["uvx", "mcp-server-git", "--repository", "/home/coder/workspace"]'
                  maxLength={2000}
                />
              </label>

              <label className={styles.field}>
                <span>
                  Environment{" "}
                  {editing && editing.env_names.length > 0
                    ? "(leave blank to keep existing)"
                    : "(JSON object)"}
                </span>
                <textarea
                  className={styles.input}
                  value={envText}
                  onChange={(event) => setEnvText(event.target.value)}
                  placeholder={'{"API_KEY": "..."}'}
                  rows={3}
                />
              </label>
            </>
          ) : (
            <>
              <label className={styles.field}>
                <span>URL</span>
                <input
                  className={styles.input}
                  value={url}
                  onChange={(event) => setUrl(event.target.value)}
                  placeholder="https://api.githubcopilot.com/mcp/"
                  maxLength={1000}
                />
              </label>

              <label className={styles.field}>
                <span>
                  Headers{" "}
                  {editing && editing.header_names.length > 0
                    ? "(leave blank to keep existing)"
                    : "(JSON object)"}
                </span>
                <textarea
                  className={styles.input}
                  value={headersText}
                  onChange={(event) => setHeadersText(event.target.value)}
                  placeholder={'{"Authorization": "Bearer ..."}'}
                  rows={3}
                />
              </label>
            </>
          )}

          <label className={styles.field}>
            <span>Timeout (seconds)</span>
            <input
              className={styles.input}
              type="number"
              min={1}
              max={60}
              value={timeoutSeconds}
              onChange={(event) => setTimeoutSeconds(event.target.value)}
            />
          </label>

          <div className={styles.toggleRow}>
            <span>Enabled</span>
            <Switch label="Enable MCP server" checked={serverEnabled} onChange={setServerEnabled} />
          </div>

          {editorError ? <p className={styles.error}>{editorError}</p> : null}
        </div>
      </Modal>

      <Modal
        open={Boolean(toolServer)}
        onClose={() => {
          setToolServer(null);
          setTools([]);
          setToolError(null);
        }}
        title={toolServer ? `${toolServer.name} tools` : "MCP tools"}
        footer={
          <>
            <Button
              variant="ghost"
              onClick={() => {
                setToolServer(null);
                setTools([]);
                setToolError(null);
              }}
            >
              Cancel
            </Button>
            <Button loading={updateServer.isPending} onClick={saveTools}>
              Save tools
            </Button>
          </>
        }
      >
        {toolError ? <p className={styles.error}>{toolError}</p> : null}
        {tools.length === 0 ? (
          <p className={styles.notice}>No tools discovered.</p>
        ) : (
          <div className={styles.toolList}>
            {tools.map((tool) => (
              <div key={tool.name} className={styles.toolRow}>
                <div className={styles.toolInfo}>
                  <strong>{tool.name}</strong>
                  <span>{tool.description || "No description"}</span>
                </div>
                <Switch
                  label={`Enable ${tool.name}`}
                  checked={!disabledTools.includes(tool.name)}
                  onChange={(checked) =>
                    setDisabledTools((current) =>
                      checked
                        ? current.filter((name) => name !== tool.name)
                        : [...current, tool.name],
                    )
                  }
                />
              </div>
            ))}
          </div>
        )}
        <p className={styles.notice}>
          All discovered tools are enabled by default. Disabled tools are hidden from agents.
        </p>
      </Modal>

      <Modal
        open={Boolean(pendingDelete)}
        onClose={() => setPendingDelete(null)}
        title="Delete MCP server"
        footer={
          <>
            <Button variant="ghost" onClick={() => setPendingDelete(null)}>
              Cancel
            </Button>
            <Button variant="danger" loading={deleteServer.isPending} onClick={handleDelete}>
              Delete
            </Button>
          </>
        }
      >
        <p>
          Delete <strong>{pendingDelete?.name}</strong>? Its tools will no longer be available to
          agents.
        </p>
      </Modal>
    </>
  );
}
