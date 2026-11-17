"use client";

import { useState } from "react";

import { Button, Modal, Switch } from "@/components/ui";
import { useMcpStatus, useReconnectMcpServer } from "@/lib/queries/mcp";
import type { McpStatusServer } from "@/lib/types";

import styles from "./mcp-chat-panel.module.css";

interface McpChatPanelProps {
  open: boolean;
  onClose: () => void;
  disabledTools: string[];
  onToggleTool: (toolName: string, enabled: boolean) => void;
  onToggleServer: (server: McpStatusServer, enabled: boolean) => void;
}

export function McpChatPanel({
  open,
  onClose,
  disabledTools,
  onToggleTool,
  onToggleServer,
}: McpChatPanelProps) {
  const { data, isLoading } = useMcpStatus(open);
  const reconnect = useReconnectMcpServer();
  const [reconnectingId, setReconnectingId] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  async function handleReconnect(server: McpStatusServer) {
    setReconnectingId(server.id);
    setMessage(null);
    try {
      const result = await reconnect.mutateAsync(server.id);
      if (!result.ok) {
        setMessage(result.error ?? `Reconnect failed for ${server.name}.`);
      } else {
        setMessage(
          `${server.name} reconnected: ${result.tools.length} tool${
            result.tools.length === 1 ? "" : "s"
          } discovered.`,
        );
      }
    } catch {
      setMessage(`Reconnect failed for ${server.name}.`);
    } finally {
      setReconnectingId(null);
    }
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="MCP tools"
      footer={
        <Button variant="secondary" onClick={onClose}>
          Close
        </Button>
      }
    >
      <p className={styles.hint}>
        Toggle MCP tools for this chat only. Global server settings live in Settings.
      </p>

      {message ? <p className={styles.notice}>{message}</p> : null}

      {isLoading ? (
        <p className={styles.muted}>Loading MCP status…</p>
      ) : !data?.feature_enabled ? (
        <p className={styles.muted}>
          MCP is disabled globally. Ask an admin to enable <code>features.mcp</code>.
        </p>
      ) : data.servers.length === 0 ? (
        <p className={styles.muted}>
          No MCP servers configured. Ask an admin to add one in Settings.
        </p>
      ) : (
        <div className={styles.servers}>
          {data.servers.map((server) => {
            const toolNames = server.tools.map((tool) => tool.name);
            const activeTools = server.tools.filter(
              (tool) => tool.enabled && !disabledTools.includes(tool.name),
            );
            const allActive = toolNames.length > 0 && activeTools.length === toolNames.length;
            const serverState = server.status ?? (server.enabled ? "not checked" : "disabled");

            return (
              <section key={server.id} className={styles.server}>
                <div className={styles.serverHeader}>
                  <div className={styles.serverInfo}>
                    <div className={styles.serverTitle}>
                      <strong>{server.name}</strong>
                      <span className={styles.transport}>{server.transport}</span>
                      <span
                        className={`${styles.status} ${
                          serverState === "ok"
                            ? styles.ok
                            : serverState === "error"
                              ? styles.fail
                              : ""
                        }`}
                      >
                        {serverState}
                      </span>
                    </div>
                    {!server.enabled ? (
                      <span className={styles.muted}>Disabled globally by an admin.</span>
                    ) : null}
                    {server.error ? <span className={styles.error}>{server.error}</span> : null}
                  </div>

                  <div className={styles.serverActions}>
                    {server.tools.length > 0 ? (
                      <span className={styles.sessionToggle}>
                        <span>Use in chat</span>
                        <Switch
                          label={`Use ${server.name} in this chat`}
                          checked={allActive}
                          onChange={(checked) => onToggleServer(server, checked)}
                          disabled={!server.enabled}
                        />
                      </span>
                    ) : null}
                    <Button
                      size="sm"
                      variant="secondary"
                      loading={reconnectingId === server.id}
                      disabled={!server.enabled}
                      onClick={() => handleReconnect(server)}
                    >
                      Reconnect
                    </Button>
                  </div>
                </div>

                {server.tools.length === 0 ? (
                  <p className={styles.muted}>No tools discovered yet. Use Reconnect to refresh.</p>
                ) : (
                  <div className={styles.tools}>
                    {server.tools.map((tool) => {
                      const checked = tool.enabled && !disabledTools.includes(tool.name);
                      return (
                        <div key={tool.name} className={styles.tool}>
                          <div className={styles.toolInfo}>
                            <strong>{tool.label}</strong>
                            <span>{tool.description || "No description"}</span>
                            <code>{tool.name}</code>
                            {!tool.enabled ? (
                              <span className={styles.muted}>Disabled globally by an admin.</span>
                            ) : null}
                          </div>
                          <Switch
                            label={`Use ${tool.label} in this chat`}
                            checked={checked}
                            onChange={(enabled) => onToggleTool(tool.name, enabled)}
                            disabled={!tool.enabled || !server.enabled}
                          />
                        </div>
                      );
                    })}
                  </div>
                )}
              </section>
            );
          })}
        </div>
      )}
    </Modal>
  );
}
